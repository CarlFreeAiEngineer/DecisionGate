import java.util.List;
import org.decisiongate.Choice;
import org.decisiongate.Criteria;
import org.decisiongate.Decisions;

/** DecisionGate from Java. Run from examples/java: mvn -q compile exec:java */
public final class Example {
    public static void main(String[] args) {
        String ticket = "Our whole warehouse can't print shipping labels and trucks leave in an hour.";
        String question = "Is the customer describing an urgent problem?";

        // A yes/no decision at the usual 0.5 cutoff.
        System.out.println("urgent: " + Decisions.isYes(ticket, question));

        // The probability, so you can keep an uncertain range for a person.
        System.out.printf("p_yes = %.3f%n", Decisions.isYesP(ticket, question));

        // Criteria and a stricter threshold.
        var criteria = new Criteria("Work is blocked and there is a deadline within hours.",
                                    "The problem is an inconvenience with no near deadline.");
        System.out.println("confident urgent: " + Decisions.isYes(ticket, question, criteria, 0.90));

        // Several options instead of yes or no.
        List<String> teams = List.of("billing", "technical support", "sales");
        for (Choice choice : Decisions.chooseP("My card was charged twice for last month's invoice.",
                                               "Which team should handle this message?", teams))
            System.out.printf("%-18s %.3f%n", teams.get(choice.index()), choice.p());
    }
}
