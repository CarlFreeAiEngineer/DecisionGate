#ifndef DECISIONGATE_H
#define DECISIONGATE_H
#include <stddef.h>
#include <stdint.h>
#if defined(_WIN32)
#define DG_API __declspec(dllimport)
#else
#define DG_API
#endif
#ifdef __cplusplus
extern "C" {
#endif

typedef struct dg_session dg_session;
typedef int32_t dg_status;
#define DG_OK 0
#define DG_INVALID_ARGUMENT 1
#define DG_LOAD_ERROR 2
#define DG_INCOMPATIBLE 3
#define DG_RESOURCE_ERROR 4
#define DG_INFERENCE_ERROR 5
#define DG_INTERNAL_ERROR 6
#define DG_INPUT_TOO_LONG 7

typedef struct dg_criteria {
    const char *yes;
    size_t yes_bytes;
    const char *no;
    size_t no_bytes;
} dg_criteria;

/* UTF-8 byte lengths exclude NUL. Borrowed input memory must remain valid for
 * the entire call. Null strings are allowed only with length zero. The question
 * and content cannot be empty. Both criteria descriptions must be nonempty when
 * criteria is supplied. Inputs over 1 MiB or the model token limit are rejected.
 * All non-null pointers must be valid and correctly aligned for their types.
 * Errors never represent a negative answer. No calls log the supplied text.
 * This is an experimental ABI; bundle matching header and library versions. */
DG_API dg_status dg_load(const char *path, size_t path_bytes, dg_session **out_model);
/* Ordinary entry point: lazily loads the bundle beside this native library on
 * the first valid call, then reuses it. Concurrent calls are serialized. Failed
 * loads can be retried. No paths or model handles are needed. The first call is
 * slower; model memory remains allocated until process exit. On Unix, load the
 * library via an absolute path so its location is unambiguous after cwd changes.
 * The same input, output, ownership and error rules as dg_evaluate apply. */
DG_API dg_status dg_is_yes_p(
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const dg_criteria *criteria, double *out_p_yes);
/* Boolean variants write 0 or 1 only on success. dg_is_yes uses p_yes >= 0.5;
 * dg_is_yes_at_threshold uses p_yes >= threshold. Threshold must be finite and
 * within [0,1]; equality counts as yes. Both share the same lazy model cache.
 * Output is unchanged on error; the status code is separate from the answer. */
DG_API dg_status dg_is_yes(
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const dg_criteria *criteria, uint8_t *out_yes);
DG_API dg_status dg_is_yes_at_threshold(
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const dg_criteria *criteria, double threshold, uint8_t *out_yes);
DG_API dg_status dg_evaluate(dg_session *model,
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const dg_criteria *criteria, double *out_p_yes);

/* Multiple choice. options/option_bytes are caller arrays of option_count
 * (2..256) nonempty UTF-8 strings. Each option is scored as a yes/no answer
 * to the question and the scores are normalized so they sum to one.
 * out_index and out_p are caller-owned arrays of option_count entries, written
 * in descending probability: out_index[0] is the best option's index into the
 * caller's options array and out_p[0] its probability. Equal probabilities keep
 * the caller's option order. Nothing is written on error. The library never
 * allocates output memory, so there is nothing to free. Optional criteria apply
 * to every option's yes/no scoring. dg_choose_p uses the lazy bundle like
 * dg_is_yes_p; dg_evaluate_choice takes an explicit session. */
DG_API dg_status dg_choose_p(
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const char *const *options, const size_t *option_bytes, size_t option_count,
    const dg_criteria *criteria, int32_t *out_index, double *out_p);
/* Writes the best option's index, or -1 when its probability is below
 * threshold (finite, within [0,1]; equality counts as chosen; 0 never defers). */
DG_API dg_status dg_choose(
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const char *const *options, const size_t *option_bytes, size_t option_count,
    const dg_criteria *criteria, double threshold, int32_t *out_index);
DG_API dg_status dg_evaluate_choice(dg_session *model,
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const char *const *options, const size_t *option_bytes, size_t option_count,
    const dg_criteria *criteria, int32_t *out_index, double *out_p);

/* Returns manifest JSON. required includes a final NUL byte. Query size using
 * buffer=NULL, capacity=0, then supply caller-owned storage. A too-small buffer
 * returns DG_RESOURCE_ERROR without modifying the buffer. */
DG_API dg_status dg_metadata(const dg_session *model,
    char *buffer, size_t capacity, size_t *required);

/* Error text belongs to the calling thread. Copy it before another API call.
 * Uses the same buffer convention as dg_metadata and preserves the error. */
DG_API dg_status dg_last_error(char *buffer, size_t capacity, size_t *required);

/* Null release is harmless. Release exactly once; never race release against
 * another call. Evaluation calls on a handle are serialized; distinct handles
 * can run independently. Each session uses at most four intra-op worker threads
 * and one inter-op thread. The ONNX Runtime remains loaded for process lifetime.
 * Keep this component loaded until process exit (dlclose/FreeLibrary unsupported).
 * Join inference threads before process exit; do not invoke it from exit hooks.
 * Handles may load different models but must use the same runtime binary hash.
 * On load failure *out_model=NULL. On evaluation failure out_p_yes is unchanged. */
DG_API void dg_release(dg_session *model);
#ifdef __cplusplus
}
#endif
#endif
