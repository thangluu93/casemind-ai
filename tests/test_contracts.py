from datetime import datetime

import pytest
from pydantic import ValidationError

from casemind.generator import SCENARIOS, document_pdf, generate_case
from casemind.models import Case, Transaction, digest


def test_seeded_case_has_stable_resolvable_records():
    for scenario in SCENARIOS:
        case = generate_case(scenario)
        assert case == generate_case(scenario)
        assert digest(case) != digest(generate_case(scenario, seed=18))
        assert scenario not in case.id
        assert Case.model_validate_json(case.model_dump_json()) == case
        assert len(case.sources) == len(set(case.sources))
        for doc in case.documents:
            assert document_pdf(doc) == document_pdf(doc)
            assert document_pdf(doc).startswith(b"%PDF")


def test_money_timezone_and_cross_record_validation():
    with pytest.raises(ValidationError):
        Transaction(id="t", sender="a", receiver="b", amount=1.2, timestamp=datetime.now())
    case = generate_case("layering").model_dump(mode="json")
    case["transactions"][0]["sender"] = "other-case-account"
    with pytest.raises(ValidationError):
        Case.model_validate(case)
    case = generate_case("layering").model_dump(mode="json")
    case["entities"][1]["id"] = case["entities"][0]["id"]
    with pytest.raises(ValidationError):
        Case.model_validate(case)
