#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Serialize original, explicitly authored synthetic examples; no model API calls."""
import json
from pathlib import Path

FAMILIES = {
    "refund": (
        "Is this purchase eligible for a refund?",
        "Yes only if the return is requested within 30 days of purchase and the item is unused. Both conditions must be explicitly established.",
        """
1|Bought yesterday; the unopened item is being returned today.|One day and unused satisfy both conditions.
0|Purchased last week, worn to a wedding, now returned.|Wearing the item violates the unused condition.
1|The sealed package was purchased 12 days ago.|Sealed and 12 days old meet the policy.
0|I bought this 31 days ago and never opened it.|The request is outside 30 days.
1|Return request on day 30; product has never been used.|Day 30 is within the inclusive deadline.
0|The product is unused, but the purchase date is unknown.|The deadline condition is not established.
1|I accidentally ordered two; this spare is untouched, bought 8 days ago.|Unused spare is within the deadline.
0|Bought 14 days ago; tested it once and disliked it.|Testing counts as use under this strict policy.
1|Purchase and return are today; packaging remains sealed.|Same-day unused return qualifies.
0|The receipt says 60 days ago; still factory sealed.|Unused status cannot override the deadline.
1|Gift purchased 20 days ago and never taken out of its box.|Both required conditions are explicit.
0|Purchased four days ago; no information about use.|Unused status is missing.
1|The duplicate order arrived untouched after purchase 29 days ago.|The item is unused and within 30 days.
0|I used the camera every day this week after buying it nine days ago.|Repeated use fails the policy.
1|The item is unused; the dated receipt is from six days ago.|Both requirements hold.
0|This unopened order was placed 90 days ago.|Purchase is too old.
1|Unused shoes bought 17 days ago are being returned.|The stated facts satisfy the rule.
0|These shoes were worn outside; purchase was two days ago.|The shoes are used.
1|I bought the lamp 25 days ago and have not used it.|Within deadline and unused.
0|The lamp is unused; I think I bought it sometime last season.|No qualifying date is established.
1|Return ticket: age 3 days; usage: none.|Both structured fields qualify.
0|Return ticket: age 3 days; usage: daily.|The usage field fails the rule.
1|Receipt age is 22 days; the headphones remain unused.|Both conditions are satisfied.
0|Receipt age is 22 days; headphones were used for a flight.|The product was used.
1|I unwrapped but never used this kettle, purchased ten days ago.|Opening packaging is not itself use under the criteria.
0|Purchased 40 days ago; customer requests an exception for an unused kettle.|The stated rule contains no exception.
1|Order is 18 days old. Item condition: unused.|Age and condition qualify.
0|I received it yesterday after purchasing it 45 days ago; it is unused.|The policy counts purchase date, not delivery date.
1|A replacement gift was bought five days ago and remains unused.|The facts satisfy both requirements.
0|My purchase was 28 days ago, and I cannot remember whether I used it.|Unused status is not established.
1|The return is requested seven days after purchase; no use occurred.|Both requirements are explicit.
0|The item was purchased 32 days ago and remains untouched.|The deadline has passed.
1|Unused backpack, purchased 26 days before this request.|The backpack satisfies both conditions.
0|Purchased 26 days ago; backpack accompanied me on a hike.|The backpack was used.
1|Return on the nineteenth day after purchase; usage log is empty and owner confirms no use.|Unused and within the period.
0|An unused keyboard is offered for return without any purchase record or date.|The date requirement is not established.
1|I bought the monitor 13 days ago, never powered it on, and have not used it.|Both conditions are explicit.
0|Bought 13 days ago and used for a single presentation.|Even one use violates the rule.
1|Receipt is dated 24 days ago; owner confirms the tool is unused.|The required facts qualify.
0|Unused tool purchased 35 days ago.|The item is outside the deadline.
""",
    ),
    "urgency": (
        "Does this message require urgent handling?",
        "Yes when a current production outage affects customers, or when the sender explicitly needs action within the next 24 hours. Otherwise no.",
        """
1|Our live checkout is down and customers cannot place orders.|A current customer-facing production outage qualifies.
0|Could you send the brochure whenever you have time?|There is no qualifying deadline or outage.
1|Please reset my account within two hours so I can submit the bid.|The explicit deadline is within 24 hours.
0|The staging environment crashed during a test.|Staging is not a customer-facing production outage.
1|Customers currently see errors instead of their invoices in production.|A current production outage affects customers.
0|URGENT: I want a nicer dashboard someday.|The word urgent alone establishes neither criterion.
1|I need approval by noon; it is now 10 a.m. on the same day.|The required action is due in two hours.
0|Please review the mockups by next Friday, seven days away.|The deadline exceeds 24 hours.
1|The public booking site is unavailable right now.|The current outage affects customers.
0|Yesterday's outage was resolved; this is a retrospective.|There is no current outage or near deadline.
1|Please send a replacement code in the next 20 minutes.|The explicit action deadline qualifies.
0|A customer suggested we add a search filter.|No current outage or deadline is stated.
1|All paying users currently fail to log in to the production service.|A current production outage affects customers.
0|My local development server will not start.|Local development failure does not meet the criteria.
1|The signed form must reach me within 24 hours.|The inclusive 24-hour limit qualifies.
0|I need the export in 25 hours.|The deadline is beyond the stated limit.
1|Please act in the next six hours to prevent our appointment being cancelled.|The required action deadline qualifies.
0|Can we discuss this at next month's meeting?|No urgent criterion applies.
1|Production search is offline for every customer at present.|A current production outage qualifies.
0|We simulated a customer outage in our sandbox.|A simulation is not a current production outage.
1|I need a decision before my train leaves in three hours.|The action deadline is within the limit.
0|This feature is important but there is no deadline.|Importance alone does not satisfy the criteria.
1|Orders cannot be submitted on the live site this morning; the fault persists.|The production outage is ongoing.
0|Our live site might fail someday if traffic grows.|A hypothetical future failure is not a current outage.
1|Please return the document within half a day.|Twelve hours is within the limit.
0|Please return the document within three business days.|The deadline does not qualify.
1|Customers are locked out of the production app right now; support confirms the incident.|Current customer outage qualifies.
0|The production app works; I am asking about a planned upgrade.|No qualifying incident or deadline exists.
1|I need the answer in 90 minutes.|The explicit deadline qualifies.
0|No rush: I am collecting ideas for next year.|Neither criterion applies.
1|Our payment endpoint is currently unavailable to real buyers.|A customer-facing production outage qualifies.
0|The test payment endpoint failed; the live endpoint is healthy.|The failure is limited to testing.
1|Please approve this within the next 18 hours.|The stated deadline is under 24 hours.
0|Can you approve this in the next 48 hours?|The deadline exceeds the limit.
1|Visitors cannot load our live storefront at the moment.|A current customer-facing outage qualifies.
0|Visitors could not load our storefront last week, but it now works.|The outage is historical and resolved.
1|The access change is needed in four hours.|The explicit action deadline qualifies.
0|The access change would be nice eventually.|No qualifying deadline is present.
1|The production delivery tracker is down for customers now.|The current production outage qualifies.
0|Our prototype tracker is broken in a private demonstration.|The prototype failure does not meet the production condition.
""",
    ),
    "duplicate": (
        "Do these reports describe the same underlying problem?",
        "Answer yes only when the reported trigger and failure match; sharing a product or feature name is not sufficient.",
        """
1|A: Exporting a PDF crashes the editor. B: The editor closes unexpectedly whenever I export as PDF.|Trigger and failure match.
0|A: PDF export crashes. B: PDF export succeeds but colors are wrong.|The failures differ.
1|A: Login loops back to sign-in after entering a valid password. B: Correct credentials return me to the login page.|Both describe the same login loop.
0|A: Login rejects valid passwords. B: Password reset email never arrives.|The triggers and failures differ.
1|A: The app freezes when sorting a table by date. B: Date-column sorting makes the application stop responding.|Same sort trigger and freeze.
0|A: Sorting by date freezes the app. B: Sorting by price gives descending instead of ascending order.|Both trigger and outcome differ.
1|A: Uploading a file over 10 MB returns error 413. B: Files larger than 10 MB fail upload with HTTP 413.|The limit and error match.
0|A: Upload over 10 MB returns 413. B: A 2 MB upload succeeds but cannot be downloaded.|Different operation and failure.
1|A: Saving an empty note produces a blank-screen crash. B: An empty note crashes to a blank screen on save.|Trigger and failure are equivalent.
0|A: Empty note crashes on save. B: Full note loses the final sentence after saving.|Different content trigger and failure.
1|A: Clicking Next on page two opens page one. B: The next-page button sends the second page back to the first.|Same navigation error.
0|A: Next returns page two to page one. B: Previous on page two does nothing.|Different controls and outcomes.
1|A: Changing language to French erases the cart. B: My cart empties when I select French as the interface language.|Same language change and data loss.
0|A: Selecting French erases the cart. B: Selecting French leaves English button labels.|Same setting but different failure.
1|A: Search for hyphenated names returns nothing. B: Names containing a hyphen get no search results.|Same input characteristic and result.
0|A: Hyphenated names return no results. B: Search returns duplicate rows for ordinary names.|Different search faults.
1|A: Muting a call also disables my camera. B: The camera turns off whenever I mute my microphone.|Same action and unintended effect.
0|A: Mute disables camera. B: Camera stays on but the video is blurred.|Different failure behavior.
1|A: Opening settings after logout crashes. B: After signing out, entering settings terminates the app.|Same sequence and crash.
0|A: Settings crashes after logout. B: Logout button is hidden inside settings.|Different problems.
1|A: Coupon SAVE5 is applied twice at checkout. B: Checkout subtracts the SAVE5 discount two times.|Same coupon and duplicated discount.
0|A: Coupon applies twice. B: Valid coupon is rejected as expired.|The failures conflict.
1|A: Deleting a folder leaves its files in search. B: Search still lists files from a folder I deleted.|Same stale search results after deletion.
0|A: Deleted folder files remain searchable. B: Folder cannot be deleted because of permissions.|Deletion succeeds in only one report.
1|A: Starting a second timer stops the first. B: My running timer halts as soon as I start another.|Same trigger and effect.
0|A: Second timer stops first. B: A single timer runs too fast.|Different timer failures.
1|A: Changing avatar rotates the uploaded image upside down. B: New profile pictures appear inverted after upload.|Same avatar orientation failure.
0|A: Avatar appears upside down. B: Avatar upload returns a network timeout.|Different failure stages.
1|A: Pressing Escape clears the whole draft. B: My draft disappears when I hit the Esc key.|Same key and data loss.
0|A: Escape deletes draft. B: Escape fails to close the help dialog.|Different affected interface and result.
1|A: Selecting dark mode makes chart labels invisible. B: Chart text disappears in the dark theme.|Same setting and visibility problem.
0|A: Dark mode hides chart labels. B: Dark mode is missing from the settings menu.|Different failures.
1|A: Renaming a workspace logs me out. B: I am signed out when I change my workspace name.|Same rename trigger and logout.
0|A: Rename logs me out. B: Rename reports success but keeps the old name.|Different outcomes.
1|A: Reordering playlist tracks duplicates the last track. B: Dragging songs into a new order adds a second copy of the final song.|Same reorder trigger and duplication.
0|A: Reordering duplicates a song. B: Playback skips a song without any reordering.|Different operations and failures.
1|A: Printing in landscape cuts off the right column. B: The rightmost column is missing on landscape printouts.|Same print setting and clipping.
0|A: Landscape printing clips a column. B: Portrait printing changes the font.|Different conditions and results.
1|A: Updating the timezone shifts saved reminders by one hour. B: Existing reminders move an hour when the timezone changes.|Same setting and shift.
0|A: Timezone update shifts reminders. B: Reminder emails are marked as spam.|Different underlying problems.
""",
    ),
    "coding_routing": (
        "Is this request about writing or debugging code rather than billing?",
        "Yes for programming implementation or debugging requests. No for payment, pricing, invoices, or account charges without a programming request.",
        """
1|How can I parse this JSON string in Rust?|This asks for programming implementation.
0|Why was my card charged twice this month?|This concerns account charges.
1|My Python loop skips the final element; how do I fix it?|This is debugging code.
0|Please send a copy of last month's invoice.|This is an invoice request.
1|What causes a null pointer error in this C function?|This asks about a programming error.
0|Can I pay the annual subscription by bank transfer?|This concerns payment methods.
1|Help me implement a retry loop for failed API calls.|This requests implementation.
0|Does your enterprise plan include a volume discount?|This concerns pricing.
1|The compiler reports an unmatched brace in my function.|This is a code compilation issue.
0|My receipt lists the wrong company address.|This concerns receipt details.
1|How do I unit-test my invoice calculation function?|The billing domain does not change that this is a programming request.
0|The invoice total looks wrong; please correct my bill.|This asks for a billing correction, not code help.
1|Write a SQL query to count unpaid invoices.|This explicitly requests code.
0|How many unpaid invoices do I owe your company?|This is an account billing question.
1|My payment webhook handler raises a type error.|This is debugging a software handler.
0|My payment was declined; can your billing team help?|No code implementation is requested.
1|How should I free memory allocated by this library?|This is a programming memory-management question.
0|I want to cancel my paid plan before renewal.|This is subscription management.
1|The JavaScript promise never resolves; help debug it.|This is programming debugging.
0|When does the introductory price expire?|This concerns pricing terms.
1|Can you translate this Java function into Kotlin?|This requests code translation.
0|Can you move my subscription charge to a different card?|This concerns payment administration.
1|I need a regular expression for postal codes.|This requests a programming expression.
0|I need a tax invoice for my purchase.|This concerns billing documentation.
1|My checkout component fails to compile after an import change.|The request describes a code compilation fault.
0|Checkout charged me for shipping twice.|This is a customer charge dispute.
1|Show me how to serialize this struct as bytes.|This requests implementation guidance.
0|What is the per-seat monthly cost?|This concerns pricing.
1|Why does my recursive function overflow the stack?|This is a code debugging question.
0|Please refund the unused part of my subscription.|This is a billing request.
1|I need help implementing authentication middleware.|This requests programming help.
0|The bank statement uses an unfamiliar merchant name for your charge.|This concerns a financial charge.
1|How do I bind this C library from Python?|This requests programming integration.
0|Please change the currency on my next invoice.|This concerns invoice administration.
1|My database migration fails with a syntax error.|This is a programming error.
0|Can the finance team explain the overdue fee?|This is a billing question.
1|Can you debug a race condition in my worker pool?|This is code debugging.
0|I bought extra seats but the receipt still shows the old amount.|This concerns billing records.
1|How can I write a test for my refund endpoint?|This explicitly requests programming work.
0|Where can I download my payment history?|This concerns account billing information.
""",
    ),
    "appointment": (
        "Is the customer asking to arrange an appointment?",
        "Yes for a request to book, move, or find availability for a meeting or consultation. No for cancellations, descriptions of past meetings, or information without a scheduling request.",
        """
1|Could I see a consultant next Tuesday?|This asks to schedule a consultation.
0|Yesterday's consultation was very helpful.|This describes a past appointment.
1|Do you have any openings this afternoon?|This asks for appointment availability.
0|Please cancel my appointment tomorrow.|Cancellation is excluded by the criteria.
1|Can we move my visit from Monday to Thursday?|This requests rescheduling.
0|What qualifications do your consultants hold?|This asks for information, not scheduling.
1|I would like to reserve a 30-minute call.|This requests a booking.
0|I missed my call yesterday and just wanted to apologize.|No request to arrange a new appointment is present.
1|Please book the earliest available session for me.|This explicitly requests a booking.
0|How much does a session cost?|This asks about price only.
1|Is there a free consultation slot after 5 p.m.?|This asks about scheduling availability.
0|Your appointment reminder has a spelling mistake.|This reports a reminder issue.
1|Could you fit me in sometime next week?|This asks for an appointment.
0|I no longer need the visit; remove it from the calendar.|This is a cancellation.
1|I'd like to change the time of my consultation.|This requests rescheduling.
0|Where is the office for my existing appointment?|This asks for location only.
1|Can you arrange a meeting with the adviser?|This explicitly requests a meeting.
0|The adviser explained everything well at our meeting.|This describes a past interaction.
1|Please put me down for the 10 a.m. opening.|This requests a specific booking.
0|Do I need to bring identification to my visit?|This asks about preparation only.
1|Are there any Saturday appointments left?|This asks about appointment availability.
0|Saturday appointments are convenient for many people.|This is a general observation, not a request.
1|May I schedule a follow-up conversation?|This explicitly requests scheduling.
0|I don't want a follow-up appointment.|This declines scheduling.
1|Can my booking be shifted an hour later?|This requests an appointment change.
0|My booking confirmation arrived an hour late.|This reports message delivery, not scheduling.
1|I need a time to talk with your specialist.|This asks to arrange a consultation.
0|What subjects does your specialist cover?|This is an informational question.
1|Would Wednesday morning work for a meeting?|This proposes a meeting time.
0|Wednesday morning was when we met last year.|This describes a past meeting.
1|Please reserve the next available video consultation.|This requests a booking.
0|I cannot attend and do not want to rebook.|This declines another appointment.
1|I'd like a slot for a review of my application.|This requests an appointment slot.
0|How long does an application review usually take?|This asks about duration only.
1|Can you offer a new time for our postponed call?|This asks to reschedule.
0|Our postponed call is no longer needed.|No scheduling request is present.
1|Let me know which times you can meet on Friday.|This requests availability.
0|Let me know what documents were discussed on Friday.|This asks about meeting content.
1|I'd like to come in for a consultation; when are you free?|This asks to arrange a visit.
0|I'm writing to say the consultation solved my problem.|This is feedback on a past consultation.
""",
    ),
}

TEST = {
    "refund": """
1|Purchase was 16 days ago; the item remains unused.|Both policy conditions hold.
0|Return on day 11, after using the product twice.|The unused condition fails.
1|Unused item being returned exactly 30 days after purchase.|The deadline includes day 30.
0|Unused item being returned 301 days after purchase.|The purchase is outside the deadline.
""",
    "urgency": """
1|I need the signed release in the next eight hours.|The explicit action deadline qualifies.
0|The release is needed 72 hours from now.|The deadline is beyond 24 hours.
1|Real customers currently cannot access our production ticket portal.|A current production outage qualifies.
0|A production outage happened this morning and has already been fixed.|The outage is no longer current.
""",
    "duplicate": """
1|A: Archiving a project removes its owner. B: The owner field becomes empty when the project is archived.|The trigger and result match.
0|A: Archive clears project owner. B: Archive button is disabled for the owner.|The failure behavior differs.
1|A: Pasting a table into a comment drops its first row. B: The top row disappears when I paste a table into comments.|Same paste trigger and lost row.
0|A: Pasted table loses a row. B: Downloaded table contains extra rows.|Different operation and failure.
""",
    "coding_routing": """
1|How do I expose a Rust function through a C interface?|This requests programming integration.
0|Which plan has the lowest annual fee?|This concerns pricing.
1|My tax calculation code returns NaN; can you help fix it?|This is code debugging despite the financial domain.
0|Please remove sales tax from my bill; I have an exemption.|This concerns a billing adjustment.
""",
    "appointment": """
1|Could we find a time for an initial discussion next month?|This asks to schedule a meeting.
0|I enjoyed our initial discussion last month.|This describes a past meeting.
1|Please transfer my Thursday slot to Friday if possible.|This requests rescheduling.
0|Please delete my Thursday slot without replacing it.|This is cancellation only.
""",
}

UNSEEN = {
    "permission": (
        "May this person edit the document under the stated rule?",
        "Only the owner or a person explicitly granted editor access may edit. Viewer access is not sufficient.",
        """
1|Mira owns the document.|The owner may edit.
0|Jon has viewer access only.|Viewer access does not permit editing.
1|The owner granted editor access to Priya.|Explicit editor access qualifies.
0|Leon has asked for editor access but the request is pending.|A pending request is not an access grant.
1|Noor is listed as an editor, although someone else owns the file.|Editors may edit without ownership.
0|Tess is a colleague of the owner and has no granted access.|A personal relationship grants no permission.
1|Ari created and still owns this document.|Current ownership permits editing.
0|Sam's editor access was revoked; Sam is now a viewer.|Current permissions do not permit editing.
1|The access list explicitly gives Lee the editor role.|The stated grant qualifies.
0|Kai can comment but has neither ownership nor editor access.|Comment permission does not satisfy the rule.
""",
    ),
    "timeline": (
        "Did the inspection happen before the delivery?",
        "Use the stated event times. Yes only if inspection is strictly earlier than delivery; simultaneous events count as no.",
        """
1|Inspection: Monday 09:00. Delivery: Monday 11:00.|The inspection happened two hours earlier.
0|Delivery was Tuesday; inspection was Wednesday of the same week.|The inspection happened later.
1|The goods were inspected Friday and delivered the following Monday.|The inspection preceded delivery.
0|Inspection and delivery both occurred at 14:30 on the same day.|Simultaneous events are not strictly earlier.
1|Delivery occurred at noon; inspection finished at 08:00 that morning.|The inspection was earlier that day.
0|The package was delivered at 07:00 and inspected at 10:00 that day.|The inspection followed delivery.
1|Inspection took place on May 2; delivery on May 3 of the same year.|May 2 precedes May 3.
0|Delivery took place on June 9; inspection on June 12 of the same year.|June 12 follows June 9.
1|Inspection was at 23:00 yesterday; delivery at 01:00 today.|The inspection was earlier across midnight.
0|Delivery was at 23:00 yesterday; inspection at 01:00 today.|The inspection was later across midnight.
""",
    ),
}

CALIBRATION = {
    "refund": """
1|The unused scarf was purchased 21 days before this return request.|Unused and within the deadline.
0|The scarf was bought 21 days ago and worn for a weekend.|It is used.
1|An unused drill bought 15 days ago is being returned.|Both conditions are established.
0|The drill is unused but was purchased 75 days ago.|The purchase is too old.
1|The owner confirms no use of the blender purchased 27 days ago.|Both requirements hold.
0|A blender bought 27 days ago was used to make breakfast.|Use fails the condition.
""",
    "urgency": """
1|Please issue the permit within 16 hours.|The explicit deadline qualifies.
0|Please issue the permit within ten days.|The deadline exceeds 24 hours.
1|Our production subscription portal is down for all customers now.|The current production outage qualifies.
0|The subscription portal failed in a rehearsal but production is healthy.|The failure is not in production.
1|I need the corrected file in 45 minutes.|The explicit action deadline qualifies.
0|The corrected file is for an archive and has no deadline.|Neither criterion applies.
""",
    "duplicate": """
1|A: Copying a board resets its due dates. B: Due dates disappear when a board is copied.|Same copying trigger and lost dates.
0|A: Copying resets dates. B: Copying preserves dates but changes the owner.|The failure differs.
1|A: Zooming a map hides all pins. B: The pins vanish when I change the map zoom.|Same zoom trigger and disappearing pins.
0|A: Zoom hides pins. B: Clicking a pin opens the wrong address.|Different trigger and effect.
""",
    "coding_routing": """
1|My HTTP client deadlocks when two tasks share a connection.|This is code debugging.
0|Please explain the charge for two extra connections on my account.|This is an account charge question.
1|How do I mock a payment gateway in a test suite?|This requests programming help.
0|Can I split my payment between two cards?|This concerns payment methods.
""",
    "appointment": """
1|Could you save a place for me in tomorrow's consultation schedule?|This requests booking.
0|Tomorrow's consultation is cancelled; I do not need another.|This is cancellation without rescheduling.
1|Is the adviser available for a call on the tenth?|This asks for appointment availability.
0|What did the adviser recommend during our call on the tenth?|This asks about past meeting content.
""",
}


def parse(text):
    return [line.split("|", 2) for line in text.strip().splitlines()]


def record(family, question, criteria, row, split, number):
    label, content, rationale = row
    identifier = f"seed-v1-{family}-{number:03d}"
    return {
        "schema_version": 1,
        "id": identifier,
        "group_id": identifier,
        "content": content,
        "question": question,
        "criteria": {"yes": criteria, "no": "Answer no when the yes conditions are not met or are not established by the state."},
        "label": int(label),
        "label_type": "binary",
        "task_family": family,
        "source": "decisionmodel-original-synthetic-seed-v1",
        "provenance": {
            "type": "synthetic",
            "generator": "AI assistant",
            "generation_recipe": "Original English cases authored in data/build_seed.py for five training families and two unseen test families; labels and rationales authored alongside each case; no external examples copied.",
            "created": "2026-09-17",
        },
        "license": "CC0-1.0",
        "rationale": rationale,
        "review_status": "synthetic_unreviewed",
        "split": split,
    }


def main():
    records = []
    for family, (question, criteria, text) in FAMILIES.items():
        rows = parse(text)
        assert len(rows) == 40, (family, len(rows))
        for i, row in enumerate(rows, 1):
            records.append(record(family, question, criteria, row, "train" if i <= 32 else "validation", i))
        for i, row in enumerate(parse(TEST[family]), 41):
            records.append(record(family, question, criteria, row, "test", i))
        for i, row in enumerate(parse(CALIBRATION[family]), 45):
            records.append(record(family, question, criteria, row, "calibration", i))
    for family, (question, criteria, text) in UNSEEN.items():
        for i, row in enumerate(parse(text), 1):
            records.append(record(family, question, criteria, row, "test", i))
    assert len(records) == 264
    target = Path(__file__).with_name("seed.jsonl")
    target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    for split in ("train", "validation", "calibration", "test"):
        subset = [r for r in records if r["split"] == split]
        print(f"{split}: {len(subset)} examples, {sum(r['label'] for r in subset)} yes")


if __name__ == "__main__":
    main()
