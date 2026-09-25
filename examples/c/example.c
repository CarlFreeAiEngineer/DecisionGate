/* DecisionGate from C. Build and run commands are in examples/README.md. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "decisiongate.h"

static int fail(void) {
    char message[512];
    size_t required = 0;
    if (dg_last_error(message, sizeof message, &required) == DG_OK)
        fprintf(stderr, "Could not evaluate the question: %s\n", message);
    else
        fputs("Could not evaluate the question.\n", stderr);
    return 1;
}

int main(void) {
    const char *ticket = "Our whole warehouse can't print shipping labels and trucks leave in an hour.";
    const char *question = "Is the customer describing an urgent problem?";
    uint8_t yes;
    double p;

    /* A yes/no decision at the usual 0.5 cutoff. NULL means no criteria. */
    if (dg_is_yes(ticket, strlen(ticket), question, strlen(question), NULL, &yes) != DG_OK) return fail();
    printf("urgent: %s\n", yes ? "true" : "false");

    /* The probability, so you can keep an uncertain range for a person. */
    if (dg_is_yes_p(ticket, strlen(ticket), question, strlen(question), NULL, &p) != DG_OK) return fail();
    printf("p_yes = %.3f\n", p);

    /* Criteria and a stricter threshold. */
    const char *yes_text = "Work is blocked and there is a deadline within hours.";
    const char *no_text = "The problem is an inconvenience with no near deadline.";
    dg_criteria criteria = {yes_text, strlen(yes_text), no_text, strlen(no_text)};
    if (dg_is_yes_at_threshold(ticket, strlen(ticket), question, strlen(question),
                               &criteria, 0.90, &yes) != DG_OK) return fail();
    printf("confident urgent: %s\n", yes ? "true" : "false");

    /* Several options instead of yes or no, best first. */
    const char *message = "My card was charged twice for last month's invoice.";
    const char *team_question = "Which team should handle this message?";
    const char *teams[] = {"billing", "technical support", "sales"};
    size_t lengths[] = {strlen(teams[0]), strlen(teams[1]), strlen(teams[2])};
    int32_t indexes[3];
    double probabilities[3];
    if (dg_choose_p(message, strlen(message), team_question, strlen(team_question),
                    teams, lengths, 3, NULL, indexes, probabilities) != DG_OK) return fail();
    for (int i = 0; i < 3; i++) printf("%-18s %.3f\n", teams[indexes[i]], probabilities[i]);
    return 0;
}
