import path from 'node:path';
import {test, expect} from '@playwright/test';

test('five live cases, scoped evidence and immutable human decisions survive reload', async ({page}) => {
  test.setTimeout(800_000);
  await page.goto('/');
  await expect(page.getByRole('heading', {name: 'Harbor transfer chain', exact: true})).toBeVisible();
  const titles = ['Harbor transfer chain', 'Harbor ownership review', 'Rowan screening review', 'Harbor document review', 'Meridian transfer circuit'];
  for (const [index, title] of titles.entries()) {
    await page.getByRole('navigation', {name: 'Synthetic investigations'}).getByRole('button').nth(index).click();
    await expect(page.getByRole('heading', {name: title, exact: true})).toBeVisible();
    await page.getByRole('button', {name: 'Start investigation', exact: false}).click();
    await expect(page.getByRole('heading', {name: 'Investigator assessment'})).toBeVisible({timeout: 150_000});
    await expect(page.getByRole('heading', {name: 'Review this version'})).toBeVisible();
    await page.locator('.evidence-item').first().click();
    await expect(page.getByRole('heading', {name: 'Evidence detail'})).toBeVisible();
    await page.locator('.source-panel .source-list button').first().click();
    await expect(page.getByRole('heading', {name: 'Source record'})).toBeVisible();
    await expect(page.locator('.source-panel pre')).toContainText('synthetic');
    await page.getByLabel('Decision', {exact: true}).selectOption('needs_follow_up');
    await page.getByLabel('Reason', {exact: true}).fill('Reviewed the source-supported observations. Request corroboration before disposition.');
    await page.getByRole('button', {name: 'Save review'}).click();
    await expect(page.locator('.review-result')).toContainText('needs follow up');
    await page.reload();
    // Returning to the same case restores the idempotent run rather than starting a new billable one.
    if (index > 0) await page.getByRole('navigation', {name: 'Synthetic investigations'}).getByRole('button').nth(index).click();
    await expect(page.locator('.review-result')).toContainText('needs follow up', {timeout: 20_000});
    const href = await page.getByRole('link', {name: 'Export JSON'}).getAttribute('href');
    const report = await (await page.request.get(href!)).json();
    const pinned = await (await page.request.get(href!.replace('/report', '/case'))).json();
    for (const doc of pinned.documents) {
      const pdf = await page.request.get(href!.replace('/report', `/documents/${doc.id}.pdf`));
      expect(pdf.status()).toBe(200);
      expect((await pdf.body()).subarray(0, 4).toString()).toBe('%PDF');
    }
    const response = await page.request.post(href!.replace('/report', '/review'), {data: {
      report_hash: report.hash, expected_version: 1, action: 'rejected', reason: 'Attempted overwrite of an existing decision'
    }});
    expect(response.status()).toBe(409);
    if (index === 0) {
      for (const width of [375, 768, 1440]) {
        await page.setViewportSize({width, height: 900});
        await page.screenshot({path: path.resolve(import.meta.dirname, `../../artifacts/e2e-report-${width}.png`), fullPage: false});
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      }
    }
  }
  const before = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage)));
  await page.getByRole('button', {name: 'Run again', exact: false}).click();
  await expect(page.getByRole('alert')).toContainText('allowance exhausted', {timeout: 20_000});
  await expect(page.getByRole('heading', {name: 'Investigator assessment'})).toBeVisible();
  await expect(page.locator('.review-result')).toContainText('needs follow up');
  expect(await page.evaluate(() => Object.fromEntries(Object.entries(localStorage)))).toEqual(before);
});
