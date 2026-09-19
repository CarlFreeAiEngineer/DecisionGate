#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Serialize original synthetic paired questions, without external model calls."""
import json
from pathlib import Path

# Each authored line is: state | yes question | yes rationale | no question | no rationale.
CASES = {
    "refund_intent": """
Please return the money I paid for this broken toaster.|Is the customer requesting a refund?|They explicitly ask for their money back.|Is the customer asking for a replacement item?|They request money, not a replacement.
The unopened package arrived today. I am keeping it.|Has the customer decided to keep the item?|They explicitly say they are keeping it.|Has the customer asked for a refund?|No request for money back is present.
I would like my payment reversed; I do not want another unit.|Does the message ask to reverse a payment?|The customer explicitly asks for reversal.|Does the customer want another unit sent?|They explicitly reject another unit.
Your refund policy page has a broken link; please fix the page.|Is this a report of a website problem?|The reported fault is a broken link.|Is this a request to refund a purchase?|The message requests a page fix, not money.
Please refund the delivery charge but leave my order in place.|Does the customer want a delivery charge refunded?|That refund is explicitly requested.|Does the customer want the entire order cancelled?|They explicitly want the order kept.
Can you send me a replacement cable? I do not need my money back.|Is the customer requesting a replacement?|They explicitly ask for a new cable.|Is the customer requesting their money back?|They explicitly say they do not need that.
I paid for two tickets but only need one. Please refund the spare ticket.|Does the customer ask for a partial refund?|They request money back for one of two tickets.|Does the customer ask to refund both tickets?|They request a refund for only the spare.
Thanks, the refund reached my bank yesterday. No further action is needed.|Does the customer confirm receiving a refund?|They say it reached their bank.|Is the customer requesting a new refund?|They report completion and request no further action.
The course was cancelled. Please reimburse my registration fee.|Does the sender want a payment returned?|Reimbursement of the fee is explicitly requested.|Is the sender asking to register for another course?|No new registration is requested.
Before I buy, how long would a refund take if I changed my mind?|Is this a question about a possible future refund?|The customer asks before buying.|Is the customer requesting a refund for an existing purchase?|The message says the purchase has not happened.
Please give me my money back for the subscription, rather than account credit.|Is a cash refund being requested?|They ask for money back instead of credit.|Would account credit satisfy the request as written?|They explicitly prefer money over credit.
I noticed your policy allows returns for unused items. Mine is still sealed; I have not decided what to do.|Is the item described as unopened?|It is explicitly still sealed.|Has the sender explicitly requested a refund?|They say they have not decided; no refund is requested.
""",
    "appointment_intent": """
Could you book me a consultation on Thursday morning?|Is the sender trying to arrange a consultation?|They explicitly request a booking.|Is the sender cancelling an existing visit?|No cancellation is requested.
Please cancel my visit; I do not want a different time.|Does the sender want the visit cancelled?|Cancellation is explicitly requested.|Is the sender asking to reschedule the visit?|They explicitly reject a different time.
I have a booking for noon. Could we move it to the afternoon?|Is the customer asking to change a booking time?|They want the existing booking moved.|Does the customer want to keep the noon time?|They explicitly ask for a later time.
The appointment reminder lists the wrong building. Please correct the address only.|Does the message report an address error?|The reminder has the wrong building.|Does the message request a different appointment time?|They ask to change only the address.
Are there any free slots for a call next week?|Is the customer asking about meeting availability?|They ask for free call slots.|Is the customer reporting a completed call?|The requested call is in the future.
Yesterday's meeting answered all my questions, so I do not need a follow-up.|Is the customer describing a past meeting?|The meeting happened yesterday.|Is the customer requesting another meeting?|They explicitly say no follow-up is needed.
Reserve the earliest appointment you have, please.|Does the message request an appointment booking?|It explicitly asks to reserve a slot.|Is this only feedback on a previous visit?|It asks for future action, not past feedback.
How much does a consultation cost? I am only comparing prices today, not booking.|Is the customer asking for pricing information?|They explicitly ask the cost.|Is the customer asking to book now?|They explicitly say they are not booking.
Could we arrange a short video meeting to discuss my application?|Is a meeting being requested?|They ask to arrange one.|Is the sender declining a proposed meeting?|No meeting is declined.
Remove my Tuesday reservation without creating a new one.|Does the sender request cancellation?|They want the reservation removed.|Does the sender request a replacement reservation?|They explicitly reject a new one.
I cannot make nine o'clock. Would ten o'clock be possible instead?|Is the sender proposing a different time?|They propose ten instead of nine.|Is the sender confirming nine o'clock works?|They explicitly cannot make nine.
What should I bring to my appointment? The existing time still works.|Is the sender asking how to prepare for a visit?|They ask what to bring.|Does the sender want to move the appointment?|They explicitly accept the existing time.
""",
    "request_routing": """
My Rust function will not compile. Can you explain this borrow error?|Is this a programming help request?|It asks about a compiler error.|Is this a dispute about a payment?|No payment is mentioned.
Please explain why this month's invoice includes an extra seat.|Does this message concern billing?|It questions an invoice charge.|Is the sender asking you to write code?|No programming action is requested.
I need a Python function that calculates sales tax.|Is the sender asking for code implementation?|They ask for a Python function.|Is the sender disputing a tax charge on their account?|They request implementation, not an account correction.
Please refund the fee on my account. I do not need help with my software.|Is the customer asking for a billing adjustment?|They want a fee refunded.|Is the customer asking for software debugging?|They explicitly say they do not need software help.
My invoice-generation script duplicates line items. Help me debug the loop.|Is debugging requested?|They explicitly ask to debug their script.|Is the sender asking for a copy of an invoice?|They request a code fix, not a document copy.
Can you email a receipt for the payment I made last week?|Is this a request for a billing document?|A receipt is requested.|Does the sender ask for an email-sending program?|They ask for a receipt, not software.
How do I call this C library from my Rust application?|Does the question concern integrating software?|It asks how to call a library.|Does the question concern the library's subscription price?|No price question is present.
Which subscription plan costs less for a team of six?|Is the customer comparing prices?|They ask which plan costs less.|Is the customer asking to debug a subscription service?|They request pricing, not debugging.
The payment webhook handler crashes with a null reference. What code change would fix it?|Is the sender seeking a code fix?|They explicitly ask for a code change.|Is the sender requesting a refund of a payment?|No return of money is requested.
My bank statement shows your company charging me twice. Please investigate the charges.|Is this a duplicate-charge complaint?|Two company charges are explicitly disputed.|Does the sender provide a programming error to debug?|No code or programming error is given.
Please show how to write a unit test for this parser.|Does this request involve software testing?|It asks for a unit test.|Does the sender ask for a payment receipt?|No receipt is requested.
Please change the company name on the invoice; the amount is correct.|Does the sender want invoice details changed?|They explicitly ask to change the name.|Does the sender dispute the amount charged?|They explicitly say the amount is correct.
My worker threads freeze while waiting on the same mutex. Can you help debug this?|Is the sender reporting a software concurrency problem?|Threads and a mutex are involved in the freeze.|Is this a complaint about a late payment?|No payment is mentioned.
What is the annual price? I am not asking how your API is implemented.|Is the sender asking about pricing?|They explicitly ask the annual price.|Is the sender requesting API implementation help?|They explicitly exclude that request.
""",
    "duplicate_reports": """
A: Exporting a spreadsheet as CSV loses all accented characters. B: Accents vanish when I save a CSV export.|Do both reports describe the same failure?|Both describe accents lost during CSV export.|Does either report describe a login failure?|Neither mentions login.
A: Uploading a photo crashes the app. B: Uploading a photo succeeds, but the image is rotated.|Do both reports concern photo uploads?|Both explicitly discuss that operation.|Do these reports describe the same failure?|A crashes; B completes with wrong orientation.
A: Clicking the bell opens a blank panel. B: The notification panel is empty when I click its bell icon.|Are the reported symptoms equivalent?|Both describe the empty panel after clicking the bell.|Do both reports say notifications arrive late?|Neither discusses delivery delay.
A: Search results are duplicated. B: Search takes thirty seconds but returns correct unique rows.|Do both reports concern search?|Both describe search behavior.|Are these reports duplicates of the same problem?|Duplicate results and slow results are different failures.
A: Pasting text removes line breaks. B: Newlines disappear from text after paste.|Do these reports describe the same text-pasting problem?|Both report line breaks lost during paste.|Does either report say copying crashes the app?|Neither reports a copy crash.
A: Deleting a note crashes the app. B: Renaming a note crashes the app.|Do both reports describe a crash?|Both explicitly report crashes.|Do the reports name the same action that triggers the crash?|Deletion and renaming are different actions.
A: After logout, Back reveals the private dashboard. B: The browser Back button shows my dashboard even after signing out.|Are both reports about private content visible after logout?|Both describe the dashboard exposed using Back.|Do either of these reports say login is impossible?|Neither reports inability to log in.
A: The Save button does nothing. B: Save works, but Open cannot read the saved file.|Do both reports mention saving a file?|Both discuss save behavior.|Do the two reports describe the same failure?|A cannot save; B saves but cannot reopen.
A: Opening the calendar changes its timezone to UTC. B: The calendar switches to UTC when I open it.|Do the trigger and result match across these reports?|Both describe opening the calendar causing the UTC change.|Do both reports say the calendar cannot be opened?|Both describe a calendar that opens.
A: PDF export drops images. B: PDF export keeps images but drops hyperlinks.|Are both reports about PDF export?|The shared operation is PDF export.|Do both reports say images are missing?|B explicitly says images remain.
A: Filtering by owner hides archived tasks. B: Archived tasks disappear when an owner filter is selected.|Are these descriptions of the same filtering symptom?|The same filter hides the same task category.|Do the reports concern changing task ownership?|They concern filtering, not ownership changes.
A: The timer stops when the laptop sleeps. B: The timer continues while the laptop sleeps and ends at the expected time.|Do both reports discuss behavior during laptop sleep?|That condition appears in both.|Do both reports describe the timer stopping during sleep?|B explicitly says the timer continues.
""",
}


def main():
    rows = []
    for family, text in CASES.items():
        for i, line in enumerate(text.strip().splitlines(), 1):
            content, yes_question, yes_reason, no_question, no_reason = line.split("|")
            split = "train" if i <= 8 else "validation" if i <= 10 else "calibration" if i == 11 else "test"
            group = f"plain-v1-{family}-{i:03d}"
            for label, question, reason in ((1, yes_question, yes_reason), (0, no_question, no_reason)):
                rows.append({
                    "schema_version": 1,
                    "id": f"{group}-{label}",
                    "group_id": group,
                    "content": content,
                    "question": question,
                    "criteria": None,
                    "label": label,
                    "label_type": "binary",
                    "task_family": family,
                    "source": "decisionmodel-original-plain-questions-v1",
                    "provenance": {
                        "type": "synthetic",
                        "generator": "OpenAI Codex assistant",
                        "generation_recipe": "Original paired English questions authored in data/build_plain_questions.py; every state has a yes and a no question in the same source group and split; no external examples copied.",
                        "created": "2026-09-17",
                    },
                    "license": "CC0-1.0",
                    "rationale": reason,
                    "review_status": "synthetic_unreviewed",
                    "split": split,
                })
    assert len(rows) == 100
    target = Path(__file__).with_name("plain-questions.jsonl")
    target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    for split in ("train", "validation", "calibration", "test"):
        subset = [row for row in rows if row["split"] == split]
        print(f"{split}: {len(subset)} examples, {sum(row['label'] for row in subset)} yes")


if __name__ == "__main__":
    main()
