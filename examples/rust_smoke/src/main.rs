//! Call DecisionGate from Rust through its C interface.
//! The library loads its model from the bundle beside it on the first call.
use std::ffi::{c_char, c_void};

// Declarations matching decisiongate.h. `criteria` is null here (no extra
// yes/no descriptions); see the header for the dg_criteria struct.
extern "C" {
    fn dg_is_yes(
        content: *const c_char, content_bytes: usize,
        question: *const c_char, question_bytes: usize,
        criteria: *const c_void, out_yes: *mut u8,
    ) -> i32;
    fn dg_is_yes_p(
        content: *const c_char, content_bytes: usize,
        question: *const c_char, question_bytes: usize,
        criteria: *const c_void, out_p_yes: *mut f64,
    ) -> i32;
    fn dg_last_error(buffer: *mut c_char, capacity: usize, required: *mut usize) -> i32;
}

fn last_error() -> String {
    let mut required = 0usize;
    unsafe { dg_last_error(std::ptr::null_mut(), 0, &mut required) };
    let mut buffer = vec![0u8; required.max(1)];
    unsafe { dg_last_error(buffer.as_mut_ptr() as *mut c_char, buffer.len(), &mut required) };
    String::from_utf8_lossy(&buffer[..required.saturating_sub(1)]).into_owned()
}

/// Safe wrapper: Ok(true/false) for an answer, Err(message) for a failure.
/// Errors are never disguised as "no".
pub fn is_yes(content: &str, question: &str) -> Result<bool, String> {
    let mut yes = 0u8;
    let status = unsafe {
        dg_is_yes(
            content.as_ptr() as *const c_char, content.len(),
            question.as_ptr() as *const c_char, question.len(),
            std::ptr::null(), &mut yes,
        )
    };
    if status == 0 { Ok(yes == 1) } else { Err(last_error()) }
}

/// Probability of yes, from 0.0 to 1.0.
pub fn is_yes_p(content: &str, question: &str) -> Result<f64, String> {
    let mut p = 0f64;
    let status = unsafe {
        dg_is_yes_p(
            content.as_ptr() as *const c_char, content.len(),
            question.as_ptr() as *const c_char, question.len(),
            std::ptr::null(), &mut p,
        )
    };
    if status == 0 { Ok(p) } else { Err(last_error()) }
}

fn main() {
    let cases = [
        ("Please return my money. The item arrived broken.", "Is the customer asking for a refund?"),
        ("Could you send me a copy of the invoice?", "Is the customer asking for a refund?"),
    ];
    for (content, question) in cases {
        match (is_yes(content, question), is_yes_p(content, question)) {
            (Ok(yes), Ok(p)) => println!("yes={yes} p_yes={p:.4}  {content}"),
            (Err(e), _) | (_, Err(e)) => {
                eprintln!("Could not evaluate the question: {e}");
                std::process::exit(1);
            }
        }
    }
    println!("Experimental model: these estimates are not reliable enough for real decisions.");
}
