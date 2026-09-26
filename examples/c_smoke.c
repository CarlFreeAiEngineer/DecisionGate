#include "decisiongator.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int report(dg_status status) {
    size_t required = 0;
    dg_last_error(NULL, 0, &required);
    char *message = malloc(required);
    if (message && dg_last_error(message, required, &required) == DG_OK)
        fprintf(stderr, "DecisionGator error %d: %s\n", status, message);
    else fprintf(stderr, "DecisionGator error %d\n", status);
    free(message);
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 1 && argc != 2 && argc != 4) {
        fprintf(stderr, "Usage: %s [BUNDLE_DIRECTORY [CONTENT QUESTION]]\n", argv[0]);
        return 2;
    }
    const char *content = argc == 4 ? argv[2] : "Please cancel my subscription before the next renewal.";
    const char *question = argc == 4 ? argv[3] : "Is the customer asking to cancel their subscription?";
    double p_yes = 0.0;
    if (argc == 1) {
        dg_status status = dg_is_yes_p(content, strlen(content), question, strlen(question), NULL, &p_yes);
        if (status != DG_OK) return report(status);
        printf("p_yes=%.9f\n", p_yes);
        /* Multiple choice: caller-owned output arrays, best option first. */
        const char *teams[] = {"billing", "technical support", "sales"};
        size_t team_bytes[3];
        int32_t rank[3];
        double p[3];
        const char *routing = "My card was charged twice for last month's invoice.";
        const char *which = "Which team should handle this message?";
        for (size_t i = 0; i < 3; ++i) team_bytes[i] = strlen(teams[i]);
        status = dg_choose_p(routing, strlen(routing), which, strlen(which), teams, team_bytes, 3, NULL, rank, p);
        if (status != DG_OK) return report(status);
        printf("top=%s p=%.9f\n", teams[rank[0]], p[0]);
        return 0;
    }
    dg_session *session = NULL;
    dg_status status = dg_load(argv[1], strlen(argv[1]), &session);
    if (status != DG_OK) return report(status);
    status = dg_evaluate(session, content, strlen(content), question, strlen(question), NULL, &p_yes);
    if (status != DG_OK) {
        int result = report(status);
        dg_release(session);
        return result;
    }
    printf("p_yes=%.9f\n", p_yes);
    dg_release(session);
    return 0;
}
