#define NAPI_VERSION 8
#include <node_api.h>
#include <string>
#include <vector>
#include <mutex>
#include <atomic>
#include "../../code/include/decisiongate.h"
#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif
using EvaluateFn = decltype(&dg_is_yes_p);
using ChooseFn = decltype(&dg_choose_p);
static std::atomic<EvaluateFn> evaluate_fn{nullptr};
static std::atomic<ChooseFn> choose_fn{nullptr};
static decltype(&dg_last_error) error_fn = nullptr;
static std::mutex initialize_mutex;
static std::string read_string(napi_env env, napi_value value) {
  size_t size = 0;
  napi_get_value_string_utf8(env, value, nullptr, 0, &size);
  std::vector<char> bytes(size + 1);
  napi_get_value_string_utf8(env, value, bytes.data(), bytes.size(), &size);
  return std::string(bytes.data(), size);
}
// Validates a JS string against the shared 1 MiB / well-formed-Unicode rule,
// throwing the appropriate JS exception and returning false on failure.
static bool check_text(napi_env env, napi_value value) {
  size_t length = 0;
  if (napi_get_value_string_utf16(env, value, nullptr, 0, &length) != napi_ok || length > 1048576) { napi_throw_range_error(env, nullptr, "Input too long"); return false; }
  std::vector<char16_t> units(length + 1);
  if (napi_get_value_string_utf16(env, value, units.data(), units.size(), &length) != napi_ok) { napi_throw_type_error(env, nullptr, "Invalid text"); return false; }
  for (size_t k = 0; k < length; ++k) {
    const auto unit = units[k];
    if (unit >= 0xD800 && unit <= 0xDBFF) {
      if (++k >= length || units[k] < 0xDC00 || units[k] > 0xDFFF) { napi_throw_type_error(env, nullptr, "Invalid Unicode"); return false; }
    } else if (unit >= 0xDC00 && unit <= 0xDFFF) { napi_throw_type_error(env, nullptr, "Invalid Unicode"); return false; }
  }
  return true;
}
static napi_value initialize(napi_env env, napi_callback_info info) {
  napi_value arg, result; size_t count = 1;
  napi_get_cb_info(env, info, &count, &arg, nullptr, nullptr);
  napi_valuetype type;
  if (count != 1 || napi_typeof(env, arg, &type) != napi_ok || type != napi_string) { napi_throw_type_error(env, nullptr, "initialize requires a library path string"); return nullptr; }
  std::lock_guard<std::mutex> guard(initialize_mutex);
  if (!evaluate_fn.load(std::memory_order_acquire)) {
    auto path = read_string(env, arg);
#ifdef _WIN32
    int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path.data(), (int)path.size(), nullptr, 0);
    std::wstring wide(size, 0);
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path.data(), (int)path.size(), wide.data(), size);
    auto handle = LoadLibraryW(wide.c_str());
    auto symbol = [&](const char* name) { return handle ? GetProcAddress(handle, name) : nullptr; };
#else
    // Deliberately pinned until process exit, as required by the native ABI.
    auto handle = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
    auto symbol = [&](const char* name) { return handle ? dlsym(handle, name) : nullptr; };
#endif
    auto eval = reinterpret_cast<EvaluateFn>(symbol("dg_is_yes_p"));
    auto error = reinterpret_cast<decltype(error_fn)>(symbol("dg_last_error"));
    if (!eval || !error) { napi_throw_error(env, nullptr, "Cannot load matching DecisionGate native library"); return nullptr; }
    // dg_choose_p may be absent from older native libraries; chooseP reports
    // DG_LOAD_ERROR at call time when so, without blocking isYesP/isYes.
    auto choose = reinterpret_cast<ChooseFn>(symbol("dg_choose_p"));
    error_fn = error; choose_fn.store(choose, std::memory_order_release); evaluate_fn.store(eval, std::memory_order_release);
  }
  napi_get_undefined(env, &result); return result;
}
struct Work {
  napi_async_work work; napi_deferred deferred;
  std::string content, question, yes, no, error;
  bool criteria = false; double answer = 0; int32_t status = 0;
};
static void execute(napi_env, void* data) {
  auto* w = static_cast<Work*>(data);
  dg_criteria criteria{w->yes.data(), w->yes.size(), w->no.data(), w->no.size()};
  w->status = evaluate_fn.load(std::memory_order_acquire)(w->content.data(), w->content.size(), w->question.data(), w->question.size(), w->criteria ? &criteria : nullptr, &w->answer);
  if (w->status) {
    size_t size = 0; error_fn(nullptr, 0, &size);
    std::vector<char> buffer(size ? size : 1);
    error_fn(buffer.data(), buffer.size(), &size);
    w->error = buffer.data();
  }
}
static void complete(napi_env env, napi_status status, void* data) {
  auto* w = static_cast<Work*>(data); napi_value value;
  if (status != napi_ok || w->status) {
    napi_value message, code;
    napi_create_string_utf8(env, w->error.empty() ? "Native work cancelled" : w->error.c_str(), NAPI_AUTO_LENGTH, &message);
    napi_create_error(env, nullptr, message, &value);
    napi_create_int32(env, w->status ? w->status : DG_INTERNAL_ERROR, &code);
    napi_set_named_property(env, value, "status", code);
    napi_reject_deferred(env, w->deferred, value);
  } else {
    napi_create_double(env, w->answer, &value); napi_resolve_deferred(env, w->deferred, value);
  }
  napi_delete_async_work(env, w->work); delete w;
}
static napi_value evaluate(napi_env env, napi_callback_info info) {
  napi_value args[4], promise, resource; size_t count = 4;
  napi_get_cb_info(env, info, &count, args, nullptr, nullptr);
  if (!evaluate_fn.load(std::memory_order_acquire) || count != 4) { napi_throw_error(env, nullptr, "Initialize DecisionGate first"); return nullptr; }
  for (size_t i = 0; i < 4; ++i) {
    napi_valuetype type;
    if (napi_typeof(env, args[i], &type) != napi_ok || (type != napi_string && !(i >= 2 && type == napi_null))) {
      napi_throw_type_error(env, nullptr, "evaluate requires content, question and two string-or-null criteria"); return nullptr;
    }
    if (type == napi_string && !check_text(env, args[i])) return nullptr;
  }
  napi_valuetype yes_type, no_type; napi_typeof(env, args[2], &yes_type); napi_typeof(env, args[3], &no_type);
  if (yes_type != no_type) { napi_throw_type_error(env, nullptr, "Supply both criteria or neither"); return nullptr; }
  auto* w = new Work;
  w->content = read_string(env, args[0]); w->question = read_string(env, args[1]);
  napi_valuetype type; napi_typeof(env, args[2], &type);
  w->criteria = type == napi_string;
  if (w->criteria) { w->yes = read_string(env, args[2]); w->no = read_string(env, args[3]); }
  napi_create_promise(env, &w->deferred, &promise);
  napi_create_string_utf8(env, "DecisionGate", NAPI_AUTO_LENGTH, &resource);
  if (napi_create_async_work(env, nullptr, resource, execute, complete, w, &w->work) != napi_ok) {
    delete w; napi_throw_error(env, nullptr, "Cannot create native work"); return nullptr;
  }
  if (napi_queue_async_work(env, w->work) != napi_ok) {
    napi_delete_async_work(env, w->work); delete w; napi_throw_error(env, nullptr, "Cannot queue native work"); return nullptr;
  }
  return promise;
}
struct ChooseWork {
  napi_async_work work; napi_deferred deferred;
  std::string content, question, yes, no, error;
  std::vector<std::string> options;
  bool criteria = false;
  std::vector<int32_t> indices;
  std::vector<double> probs;
  int32_t status = 0;
};
static void execute_choose(napi_env, void* data) {
  auto* w = static_cast<ChooseWork*>(data);
  auto choose = choose_fn.load(std::memory_order_acquire);
  if (!choose) { w->status = DG_LOAD_ERROR; w->error = "Loaded DecisionGate native library does not provide dg_choose_p"; return; }
  std::vector<const char*> option_ptrs(w->options.size());
  std::vector<size_t> option_bytes(w->options.size());
  for (size_t i = 0; i < w->options.size(); ++i) { option_ptrs[i] = w->options[i].data(); option_bytes[i] = w->options[i].size(); }
  w->indices.assign(w->options.size(), 0);
  w->probs.assign(w->options.size(), 0.0);
  dg_criteria criteria{w->yes.data(), w->yes.size(), w->no.data(), w->no.size()};
  w->status = choose(w->content.data(), w->content.size(), w->question.data(), w->question.size(),
                      option_ptrs.data(), option_bytes.data(), option_ptrs.size(),
                      w->criteria ? &criteria : nullptr, w->indices.data(), w->probs.data());
  if (w->status) {
    size_t size = 0; error_fn(nullptr, 0, &size);
    std::vector<char> buffer(size ? size : 1);
    error_fn(buffer.data(), buffer.size(), &size);
    w->error = buffer.data();
  }
}
static void complete_choose(napi_env env, napi_status status, void* data) {
  auto* w = static_cast<ChooseWork*>(data); napi_value value;
  if (status != napi_ok || w->status) {
    napi_value message, code;
    napi_create_string_utf8(env, w->error.empty() ? "Native work cancelled" : w->error.c_str(), NAPI_AUTO_LENGTH, &message);
    napi_create_error(env, nullptr, message, &value);
    napi_create_int32(env, w->status ? w->status : DG_INTERNAL_ERROR, &code);
    napi_set_named_property(env, value, "status", code);
    napi_reject_deferred(env, w->deferred, value);
  } else {
    napi_create_array_with_length(env, w->indices.size(), &value);
    for (size_t i = 0; i < w->indices.size(); ++i) {
      napi_value entry, index, p;
      napi_create_object(env, &entry);
      napi_create_int32(env, w->indices[i], &index);
      napi_create_double(env, w->probs[i], &p);
      napi_set_named_property(env, entry, "index", index);
      napi_set_named_property(env, entry, "p", p);
      napi_set_element(env, value, static_cast<uint32_t>(i), entry);
    }
    napi_resolve_deferred(env, w->deferred, value);
  }
  napi_delete_async_work(env, w->work); delete w;
}
static napi_value choose_p(napi_env env, napi_callback_info info) {
  napi_value args[5], promise, resource; size_t count = 5;
  napi_get_cb_info(env, info, &count, args, nullptr, nullptr);
  if (!evaluate_fn.load(std::memory_order_acquire) || count != 5) { napi_throw_error(env, nullptr, "Initialize DecisionGate first"); return nullptr; }
  napi_valuetype type;
  for (size_t i = 0; i < 2; ++i) {
    if (napi_typeof(env, args[i], &type) != napi_ok || type != napi_string) { napi_throw_type_error(env, nullptr, "chooseP requires content and question strings"); return nullptr; }
    if (!check_text(env, args[i])) return nullptr;
  }
  bool is_array = false;
  if (napi_is_array(env, args[2], &is_array) != napi_ok || !is_array) { napi_throw_type_error(env, nullptr, "chooseP requires an options array"); return nullptr; }
  uint32_t length = 0;
  napi_get_array_length(env, args[2], &length);
  if (length < 2) { napi_throw_range_error(env, nullptr, "chooseP requires at least two options"); return nullptr; }
  std::vector<std::string> options(length);
  for (uint32_t i = 0; i < length; ++i) {
    napi_value item;
    if (napi_get_element(env, args[2], i, &item) != napi_ok || napi_typeof(env, item, &type) != napi_ok || type != napi_string) {
      napi_throw_type_error(env, nullptr, "chooseP options must be strings"); return nullptr;
    }
    if (!check_text(env, item)) return nullptr;
    options[i] = read_string(env, item);
  }
  napi_valuetype yes_type, no_type; napi_typeof(env, args[3], &yes_type); napi_typeof(env, args[4], &no_type);
  if (yes_type != no_type || (yes_type != napi_string && yes_type != napi_null)) { napi_throw_type_error(env, nullptr, "Supply both criteria or neither"); return nullptr; }
  auto* w = new ChooseWork;
  w->content = read_string(env, args[0]); w->question = read_string(env, args[1]);
  w->options = std::move(options);
  w->criteria = yes_type == napi_string;
  if (w->criteria) { w->yes = read_string(env, args[3]); w->no = read_string(env, args[4]); }
  napi_create_promise(env, &w->deferred, &promise);
  napi_create_string_utf8(env, "DecisionGate.choose", NAPI_AUTO_LENGTH, &resource);
  if (napi_create_async_work(env, nullptr, resource, execute_choose, complete_choose, w, &w->work) != napi_ok) {
    delete w; napi_throw_error(env, nullptr, "Cannot create native work"); return nullptr;
  }
  if (napi_queue_async_work(env, w->work) != napi_ok) {
    napi_delete_async_work(env, w->work); delete w; napi_throw_error(env, nullptr, "Cannot queue native work"); return nullptr;
  }
  return promise;
}
static napi_value init(napi_env env, napi_value exports) {
  napi_property_descriptor properties[] = {
    {"initialize", nullptr, initialize, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"evaluate", nullptr, evaluate, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"chooseP", nullptr, choose_p, nullptr, nullptr, nullptr, napi_default, nullptr}
  };
  napi_define_properties(env, exports, 3, properties); return exports;
}
NAPI_MODULE(NODE_GYP_MODULE_NAME, init)
