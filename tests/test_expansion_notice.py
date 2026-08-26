from dusty_dragon.organization.expansion_notice import ExpansionNotice
from dusty_dragon.organization.expansion_roadmap import (
    DeskTier,
    ExpansionRecommendation,
)


def test_expansion_notice_targets_firm_email_and_describes_manual_account_setup():
    notice = ExpansionNotice(
        recommendation=ExpansionRecommendation(
            eligible=True,
            reason="scalping division has 1/6 qualified desks",
            tier=DeskTier.STYLE,
            style="scalping",
            next_slot=2,
        )
    )

    body = notice.to_text()

    assert notice.recipient == "forex.isekai@gmail.com"
    assert notice.subject == "Dusty Dragon Trading Firm — Expansion Request"
    assert "scalping" in body
    assert "Requested desk slot: 2" in body
    assert "manually" in body
    assert "must not create brokerage accounts" in body


def test_no_expansion_notice_does_not_request_account_creation():
    notice = ExpansionNotice(
        recommendation=ExpansionRecommendation(
            eligible=False,
            reason="configured corporate expansion roadmap is fully populated",
        )
    )

    assert "no currently eligible" in notice.to_text()
