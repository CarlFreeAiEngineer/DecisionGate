//! Points the linker at a DecisionGate release bundle.
//! Set DECISIONGATE_BUNDLE to the bundle directory; the default is the bundle
//! for this host under released/.
use std::{env, path::PathBuf};

fn main() {
    let default = if cfg!(target_os = "macos") {
        "macos-arm64"
    } else if cfg!(target_os = "windows") {
        "windows-x64"
    } else {
        "linux-x64"
    };
    let bundle = env::var("DECISIONGATE_BUNDLE").map(PathBuf::from).unwrap_or_else(|_| {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../released").join(default)
    });
    let bundle = bundle.canonicalize().expect("DecisionGate bundle directory not found");
    println!("cargo:rerun-if-env-changed=DECISIONGATE_BUNDLE");
    println!("cargo:rustc-link-search=native={}", bundle.display());
    println!("cargo:rustc-link-lib=dylib=decisiongate");
    if !cfg!(target_os = "windows") {
        // Let the executable find the library at run time without any setup.
        println!("cargo:rustc-link-arg=-Wl,-rpath,{}", bundle.display());
    }
}
