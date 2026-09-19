// Calls the component the way an application would. Point DECISIONGATE_BUNDLE at a
// release bundle (for example released/macos-arm64) or set Bundle.Directory first.
using DecisionGate;

var cases = new[]
{
    ("Please return my money. The item arrived broken.", "Is the customer asking for a refund?"),
    ("Could you send me a copy of the invoice?", "Is the customer asking for a refund?"),
};
foreach (var (content, question) in cases)
    Console.WriteLine($"yes={Decisions.IsYes(content, question)} p_yes={Decisions.IsYesP(content, question):F4}  {content}");

var strict = Decisions.IsYes(
    "Please cancel my subscription before the next renewal.",
    "Is the customer asking to cancel their subscription?",
    new Criteria("The customer wants their subscription to end.",
                 "The customer asks about anything other than ending the subscription."),
    threshold: 0.9);
Console.WriteLine($"cancel at 0.9 with criteria: {strict}");

var teams = new[] { "billing", "technical support", "sales" };
int team = Decisions.Choose("My card was charged twice for last month's invoice.", "Which team should handle this message?", teams);
Console.WriteLine($"choose -> {team} ({teams[team]})");
foreach (var c in Decisions.ChooseP("My card was charged twice for last month's invoice.", "Which team should handle this message?", teams))
    Console.WriteLine($"  {c.P:F3} {teams[c.Index]}");

try { Decisions.IsYes("", "empty content?"); }
catch (DecisionGateException e) { Console.WriteLine($"error reported as exception (status {e.StatusCode}): {e.Message}"); }
Console.WriteLine("Synthetic-benchmark model: about 92% on held-out tests; measure on your own data before relying on it.");
