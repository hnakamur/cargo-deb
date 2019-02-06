use std::process::Command;

fn main() {
    let search_dir = Command::new("sh")
        .args(&["-c", "gcc -print-search-dirs | sed -ne 's/^install: //p'"])
        .output().expect("failed to find gcc install dir").stdout;
    println!("cargo:rustc-link-lib=static=backtrace");
    println!("cargo:rustc-link-search=native={}", String::from_utf8(search_dir).unwrap().trim_right());
    println!("dh-cargo:deb-built-using=backtrace=0~={}", "libgcc-[0-9]+-dev .*");
}
