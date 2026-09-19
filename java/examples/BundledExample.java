import org.decisiongate.Criteria;
import org.decisiongate.DecisionGateException;
import org.decisiongate.Decisions;

/** Run with the API, JNA, and native bundle JARs on the classpath. */
public final class BundledExample {
    public static void main(String[] args) {
        if (args.length != 0) System.setProperty("decisiongate.cache", args[0]);
        double yes = Decisions.isYesP("Please return my money. The item arrived broken.",
                "Is the customer asking for a refund?");
        double no = Decisions.isYesP("Could you send me a copy of the invoice?",
                "Is the customer asking for a refund?");
        if (Math.abs(yes - 0.9962034385661188) > 1e-6
                || Math.abs(no - 0.005127448912056216) > 1e-6) {
            throw new AssertionError("Java/native prediction mismatch");
        }
        System.out.printf("Refund request: %.6f%nInvoice request: %.6f%n", yes, no);
        String refund = "Please return my money. The item arrived broken.";
        String question = "Is the customer asking for a refund?";
        if (!Decisions.isYes(refund, question)
                || Decisions.isYes("Could you send me a copy of the invoice?", question)
                || !Decisions.isYes(refund, question, yes)
                || Decisions.isYes(refund, question, Math.nextUp(yes))
                || !Decisions.isYes(refund, question, 0.0)
                || Decisions.isYes(refund, question, 1.0)) {
            throw new AssertionError("Boolean decision or inclusive threshold mismatch");
        }
        double criteria = Decisions.isYesP("Please cancel Renée’s café subscription. ☕",
                "Is cancellation requested?",
                new Criteria("An explicit request to cancel.", "No cancellation request."));
        if (Math.abs(criteria - 0.061476134239817716) > 1e-6) {
            throw new AssertionError("Java/native criteria mismatch");
        }
        Criteria descriptions = new Criteria("An explicit request to cancel.", "No cancellation request.");
        if (Decisions.isYes("Please cancel Renée’s café subscription. ☕",
                "Is cancellation requested?", descriptions)
                || !Decisions.isYes("Please cancel Renée’s café subscription. ☕",
                "Is cancellation requested?", descriptions, 0.05)) {
            throw new AssertionError("Boolean criteria mismatch");
        }
        try {
            Decisions.isYes("x".repeat(1_048_577), question);
            throw new AssertionError("Native failure became a boolean answer");
        } catch (DecisionGateException expected) {
            if (expected.statusCode() != 7) throw expected;
        }
        System.out.println("Bundled Java inference passed; DecisionGate remains experimental.");
    }
}
