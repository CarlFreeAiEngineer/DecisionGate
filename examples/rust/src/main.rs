//! Call DecisionGate from Rust through its C interface.
//! The library loads its model from the bundle beside it on the first call.
use std::ffi::c_char;

/// Optional descriptions of what counts as yes and as no (dg_criteria in decisiongate.h).
#[repr(C)]
pub struct Criteria {
    yes: *const c_char,
    yes_bytes: usize,
    no: *const c_char,
    no_bytes: usize,
}

impl Criteria {
    pub fn new(yes: &'static str, no: &'static str) -> Self {
        Criteria { yes: yes.as_ptr().cast(), yes_bytes: yes.len(), no: no.as_ptr().cast(), no_bytes: no.len() }
    }
}

// Declarations matching decisiongate.h.
extern "C" {
    fn dg_is_yes_at_threshold(
        content: *const c_char, content_bytes: usize,
        question: *const c_char, question_bytes: usize,
        criteria: *const Criteria, threshold: f64, out_yes: *mut u8,
    ) -> i32;
    fn dg_is_yes_p(
        content: *const c_char, content_bytes: usize,
        question: *const c_char, question_bytes: usize,
        criteria: *const Criteria, out_p_yes: *mut f64,
    ) -> i32;
    fn dg_choose_p(
        content: *const c_char, content_bytes: usize,
        question: *const c_char, question_bytes: usize,
        options: *const *const c_char, option_bytes: *const usize, option_count: usize,
        criteria: *const Criteria, out_index: *mut i32, out_p: *mut f64,
    ) -> i32;
    fn dg_last_error(buffer: *mut c_char, capacity: usize, required: *mut usize) -> i32;
}

fn last_error() -> String {
    let mut required = 0usize;
    unsafe { dg_last_error(std::ptr::null_mut(), 0, &mut required) };
    let mut buffer = vec![0u8; required.max(1)];
    unsafe { dg_last_error(buffer.as_mut_ptr().cast(), buffer.len(), &mut required) };
    String::from_utf8_lossy(&buffer[..required.saturating_sub(1)]).into_owned()
}

fn check(status: i32) -> Result<(), String> {
    if status == 0 { Ok(()) } else { Err(last_error()) }
}

fn criteria_ptr(criteria: Option<&Criteria>) -> *const Criteria {
    criteria.map_or(std::ptr::null(), |c| c as *const Criteria)
}

/// Ok(true/false) for an answer, Err(message) for a failure. Errors are never disguised as "no".
pub fn is_yes(content: &str, question: &str, criteria: Option<&Criteria>, threshold: f64) -> Result<bool, String> {
    let mut yes = 0u8;
    check(unsafe {
        dg_is_yes_at_threshold(content.as_ptr().cast(), content.len(), question.as_ptr().cast(), question.len(),
                               criteria_ptr(criteria), threshold, &mut yes)
    })?;
    Ok(yes == 1)
}

/// Probability of yes, from 0.0 to 1.0.
pub fn is_yes_p(content: &str, question: &str, criteria: Option<&Criteria>) -> Result<f64, String> {
    let mut p = 0f64;
    check(unsafe {
        dg_is_yes_p(content.as_ptr().cast(), content.len(), question.as_ptr().cast(), question.len(),
                    criteria_ptr(criteria), &mut p)
    })?;
    Ok(p)
}

/// Every option as (index, probability), best first.
pub fn choose_p(content: &str, question: &str, options: &[&str]) -> Result<Vec<(usize, f64)>, String> {
    let pointers: Vec<*const c_char> = options.iter().map(|o| o.as_ptr().cast()).collect();
    let lengths: Vec<usize> = options.iter().map(|o| o.len()).collect();
    let mut indexes = vec![0i32; options.len()];
    let mut probabilities = vec![0f64; options.len()];
    check(unsafe {
        dg_choose_p(content.as_ptr().cast(), content.len(), question.as_ptr().cast(), question.len(),
                    pointers.as_ptr(), lengths.as_ptr(), options.len(), std::ptr::null(),
                    indexes.as_mut_ptr(), probabilities.as_mut_ptr())
    })?;
    Ok(indexes.into_iter().map(|i| i as usize).zip(probabilities).collect())
}

fn run() -> Result<(), String> {
    let ticket = "Our whole warehouse can't print shipping labels and trucks leave in an hour.";
    let question = "Is the customer describing an urgent problem?";

    // A yes/no decision at the usual 0.5 cutoff.
    println!("urgent: {}", is_yes(ticket, question, None, 0.5)?);

    // The probability, so you can keep an uncertain range for a person.
    println!("p_yes = {:.3}", is_yes_p(ticket, question, None)?);

    // Criteria and a stricter threshold.
    let criteria = Criteria::new("Work is blocked and there is a deadline within hours.",
                                 "The problem is an inconvenience with no near deadline.");
    println!("confident urgent: {}", is_yes(ticket, question, Some(&criteria), 0.90)?);

    // Several options instead of yes or no.
    let teams = ["billing", "technical support", "sales"];
    for (index, p) in choose_p("My card was charged twice for last month's invoice.",
                               "Which team should handle this message?", &teams)? {
        println!("{:<18} {p:.3}", teams[index]);
    }
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Could not evaluate the question: {e}");
        std::process::exit(1);
    }
}
