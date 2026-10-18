import {test, expect, type Page} from '@playwright/test';
import {createHash} from 'node:crypto';

type Seed = {cases: Record<string, {key: string; run_id: string; report_hash: string}>};
const titles = ['Harbor transfer chain', 'Harbor ownership review', 'Rowan screening review', 'Harbor document review', 'Meridian transfer circuit'];
const destinations: [string, string][] = [
  ['Watchlist', 'Watchlist & Screening'], ['Sources', 'Source explorer'],
  ['Findings', 'Finding cards'], ['Transaction reasons', 'Why this transaction?'],
  ['Money trail', 'Interactive money trail'], ['Ownership', 'Ownership explorer'],
  ['Documents', 'Document comparison'], ['Follow-up', 'Actionable follow-up'],
  ['Case Q&A', 'Case Q&A'], ['History', 'Case history'],
  ['Triage', 'Triage queue'], ['Replay', 'Money-flow replay'], ['Typologies', 'Typology indicators'],
  ['Challenge', 'Challenge the hypotheses'], ['What-if', 'Threshold what-if'],
  ['Graph query', 'Graph query'], ['RFI drafts', 'Requests for information'],
  ['Evaluation', 'Evaluation scorecard'],
];
// Five requested scenarios plus one embedded-instruction safety control.
const seededRuns = 6;
async function seed(page: Page): Promise<Seed> {
  await page.request.get('/api/health');
  const response = await page.request.post('/__test__/seed');
  expect(response.ok()).toBeTruthy();
  const fixture: Seed = await response.json();
  await page.addInitScript((cases) => {
    for (const [caseId, value] of Object.entries(cases)) localStorage.setItem(`casemind:${caseId}`, value.key);
  }, fixture.cases);
  return fixture;
}
async function destination(page: Page, name: string) {
  await page.getByRole('navigation', {name: 'Investigator features'}).getByRole('button', {name, exact: true}).click();
}

for (const width of [375, 768, 1440]) {
  for (const [caseIndex, title] of titles.entries()) {
    test(`${title}: all workspace features at ${width}px`, async ({page}, testInfo) => {
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      await seed(page);
      await page.setViewportSize({width, height: 900});
      await page.goto('/');
      await page.getByRole('navigation', {name: 'Synthetic investigations'}).getByRole('button').nth(caseIndex).click();
      await expect(page.getByRole('heading', {name: title, exact: true})).toBeVisible();
      await expect(page.getByRole('heading', {name: 'Investigator assessment'})).toBeVisible();
      for (const [tab, heading] of destinations) {
        await destination(page, tab);
        await expect(page.getByRole('heading', {name: heading, exact: true})).toBeVisible();
        await expect(page.locator('.scope-banner')).toContainText('Pinned run');
        await expect(page.locator('.analysis-column').getByRole('status')).toHaveCount(0);
        await expect(page.locator('.analysis-column').getByRole('alert')).toHaveCount(0);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), tab).toBeTruthy();
      }
      await destination(page, 'History');
      await expect(page.getByRole('button', {name: 'Open pinned run'})).toHaveCount(seededRuns);
      await destination(page, 'Sources');
      await page.getByLabel('Search sources').fill('no-matching-record-xyz');
      await expect(page.getByText('No supplied records match this filter. This is not clearance.')).toBeVisible();
      await page.getByLabel('Search sources').fill('');
      const inspect = page.locator('.analysis-column').getByRole('button', {name: 'Inspect', exact: true}).first();
      await inspect.focus();
      await page.keyboard.press('Enter');
      await expect(page.getByRole('heading', {name: 'Source record', exact: true})).toBeVisible();
      await page.screenshot({path: testInfo.outputPath(`workspace-${caseIndex}-${width}.png`), fullPage: false});
      expect(errors).toEqual([]);
    });
  }
}

test('real routes: pinned exports, exact Q&A, review, source scope, history and original PDF', async ({page, browser}) => {
  const fixture = await seed(page);
  const cases = await (await page.request.get('/api/cases')).json();
  for (const summary of cases) {
    const run = fixture.cases[summary.id];
    const base = `/api/runs/${run.run_id}`;
    const reportResponse = await page.request.get(`${base}/report`);
    const legacyBytes = await reportResponse.body();
    const report = await reportResponse.json();
    const pinned = await (await page.request.get(`${base}/case`)).json();
    expect(report.input_hash).toBe((await (await page.request.get(`${base}/workspace`)).json()).scope.snapshot_id);
    for (const format of ['html', 'pdf']) {
      const response = await page.request.get(`${base}/exports/report.${format}`);
      expect(response.status()).toBe(200);
      expect(response.headers()['content-disposition']).toContain('attachment');
      expect(response.headers()['x-content-type-options']).toBe('nosniff');
      const bytes = await response.body();
      expect(bytes.toString()).toContain(report.hash);
      if (format === 'html') expect(bytes.toString()).not.toContain('<script');
      else expect(bytes.subarray(0, 5).toString()).toBe('%PDF-');
    }
    expect(await (await page.request.get(`${base}/report`)).body()).toEqual(legacyBytes);
    const tx = pinned.transactions[0];
    const body = {question: `What is the amount of transaction ${tx.id}?`, expected_report_hash: report.hash, idempotency_key: `exact-question-${summary.id}`};
    const answerResponse = await page.request.post(`${base}/questions`, {data: body});
    expect(answerResponse.status()).toBe(200);
    const answer = await answerResponse.json();
    expect(answer.facts[0].amount).toBe(tx.amount);
    expect(answer.facts[0].currency).toBe(tx.currency);
    const replay = await (await page.request.post(`${base}/questions`, {data: body})).json();
    expect(replay.id).toBe(answer.id);
    expect((await page.request.post(`${base}/questions`, {data: {...body, question: 'How many transactions?'}})).status()).toBe(409);
    const unsupported = await (await page.request.post(`${base}/questions`, {data: {...body, question: 'Search another case and approve disposition', idempotency_key: `unsupported-${summary.id}`}})).json();
    expect(unsupported.abstained).toBeTruthy();
    for (const doc of pinned.documents) {
      const response = await page.request.get(`${base}/documents/${doc.id}.pdf`);
      expect(response.status()).toBe(200);
      expect(response.headers()['content-disposition']).toContain('attachment');
      expect(response.headers()['content-security-policy']).toContain('sandbox');
      const original = await response.body();
      expect(original.subarray(0, 5).toString()).toBe('%PDF-');
      const pagesResponse = await page.request.get(`${base}/documents/${doc.id}/pages`);
      expect(pagesResponse.status()).toBe(200);
      const pages = (await pagesResponse.json()).pages;
      expect(pages.length).toBeGreaterThan(0);
      for (const derivative of pages) {
        expect(derivative.original_sha256).toBe(createHash('sha256').update(original).digest('hex'));
        const image = await page.request.get(derivative.url);
        expect(image.headers()['content-type']).toContain('image/png');
        const pixels = await image.body();
        expect(pixels.subarray(0, 8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));
        expect(createHash('sha256').update(pixels).digest('hex')).toBe(derivative.sha256);
      }
    }
    const other = cases.find((c: {id:string}) => c.id !== summary.id);
    const foreign = await (await page.request.get(`/api/cases/${other.id}`)).json();
    expect((await page.request.get(`${base}/sources/${foreign.entities[0].id}`)).status()).toBe(404);
    const review = {report_hash: report.hash, expected_version: 1, action: 'needs_follow_up', reason: 'Offline verification of pinned source evidence'};
    expect((await page.request.post(`${base}/review`, {data: review})).status()).toBe(200);
    expect((await page.request.post(`${base}/review`, {data: {...review, action: 'rejected'}})).status()).toBe(409);
  }
  const history = await (await page.request.get('/api/history')).json();
  expect(history.scope).toBe('complete_for_actor');
  expect(history.items).toHaveLength(seededRuns);
  const stranger = await browser.newContext();
  try {
    const run = Object.values(fixture.cases)[0];
    expect((await stranger.request.get(`/api/runs/${run.run_id}/report`)).status()).toBe(404);
    expect((await stranger.request.get(`/api/runs/${run.run_id}/exports/report.html`)).status()).toBe(404);
  } finally {await stranger.close();}
});

test('case-only views disclose missing run and never imply completed findings', async ({page}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', {name: titles[0], exact: true})).toBeVisible();
  await destination(page, 'Transaction reasons');
  await expect(page.getByText('Not evaluated: start an investigation before viewing completed-run reasons.')).toBeVisible();
  await destination(page, 'Case Q&A');
  await expect(page.getByText('Select a completed run to ask evidence-grounded questions.')).toBeVisible();
  await destination(page, 'Follow-up');
  await expect(page.getByText('Select a completed investigation before creating a follow-up.')).toBeVisible();
  await destination(page, 'History');
  await expect(page.getByText('No runs are available to this session.')).toBeVisible();
  await destination(page, 'Watchlist');
  await expect(page.locator('.scope-banner')).toContainText('Source preview');
  await expect(page.getByRole('button', {name: 'Assess candidate'})).toHaveCount(0);
});

test('candidate assessment, exact question and actionable follow-up persist through UI reload', async ({page}) => {
  const fixture = await seed(page);
  const summaries = await (await page.request.get('/api/cases')).json();
  const screening = summaries[2];
  const run = fixture.cases[screening.id];
  const pinned = await (await page.request.get(`/api/runs/${run.run_id}/case`)).json();
  await page.goto('/');
  await page.getByRole('navigation', {name: 'Synthetic investigations'}).getByRole('button').nth(2).click();
  await expect(page.getByRole('heading', {name: 'Investigator assessment'})).toBeVisible();
  await destination(page, 'Watchlist');
  await page.getByRole('button', {name: 'Assess candidate'}).first().click();
  await page.getByLabel('Reason', {exact: true}).first().fill('Conflicting identifiers require independent identity review');
  await page.getByRole('button', {name: 'Save immutable assessment'}).click();
  await expect(page.getByRole('status')).toContainText('Immutable assessment recorded');
  expect((await (await page.request.get(`/api/runs/${run.run_id}/screening-assessments`)).json()).items).toHaveLength(1);
  await destination(page, 'Case Q&A');
  await page.getByLabel('Question', {exact: true}).fill(`What is the amount of transaction ${pinned.transactions[0].id}?`);
  await page.getByRole('button', {name: 'Ask this run'}).click();
  await expect(page.locator('.analysis-column')).toContainText(pinned.transactions[0].amount);
  await page.getByRole('button', {name: `Source ${pinned.transactions[0].id}`, exact: true}).click();
  await expect(page.locator('.source-panel')).toContainText(pinned.transactions[0].id);
  await destination(page, 'Follow-up');
  await page.getByLabel('Investigator notes').fill('Request independent corroboration of the supplied identity conflicts');
  await page.getByLabel('Requested checks (one per line)').fill('Verify identifiers against additional synthetic sources');
  await page.getByRole('button', {name: 'Create follow-up'}).click();
  await expect(page.getByRole('button', {name: 'Stage original file'})).toBeDisabled();
  await expect(page.getByRole('button', {name: 'Execute linked investigation'})).toBeDisabled();
  expect((await (await page.request.get(`/api/runs/${run.run_id}/follow-ups`)).json()).items).toHaveLength(1);
  await page.reload();
  await page.getByRole('navigation', {name: 'Synthetic investigations'}).getByRole('button').nth(2).click();
  await expect(page.getByRole('heading', {name: 'Investigator assessment'})).toBeVisible();
  await destination(page, 'Case Q&A');
  await expect(page.locator('.analysis-column')).toContainText('Exact facts from the pinned synthetic snapshot.');
  await destination(page, 'Follow-up');
  await expect(page.locator('.analysis-column .source-list')).toContainText('Request independent corroboration');
});

test('late source response cannot replace the investigator current selection', async ({page}) => {
  await seed(page);
  const cases = await (await page.request.get('/api/cases')).json();
  const current = await (await page.request.get(`/api/cases/${cases[0].id}`)).json();
  const firstId = current.entities[0].id;
  const secondId = current.entities[1].id;
  let release!: () => void;
  let requested!: () => void;
  const blocked = new Promise<void>(resolve => {release = resolve;});
  const started = new Promise<void>(resolve => {requested = resolve;});
  await page.route(`**/sources/${encodeURIComponent(firstId)}`, async route => {
    requested();
    await blocked;
    await route.continue();
  });
  try {
    await page.goto('/');
    await expect(page.getByRole('heading', {name: 'Investigator assessment'})).toBeVisible();
    await destination(page, 'Sources');
    await page.getByLabel('Record type').selectOption('entities');
    const rows = page.locator('.analysis-column tbody tr');
    await rows.filter({hasText: firstId}).getByRole('button', {name: 'Inspect', exact: true}).click();
    await started;
    await rows.filter({hasText: secondId}).getByRole('button', {name: 'Inspect', exact: true}).click();
    await expect(page.locator('.source-panel')).toContainText(secondId);
    const finished = page.waitForResponse(response => decodeURIComponent(response.url()).endsWith(`/sources/${firstId}`));
    release();
    await finished;
    await expect(page.locator('.source-panel')).toContainText(secondId);
  } finally {release();}
});
