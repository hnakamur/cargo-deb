extern crate aho_corasick;
extern crate regex;

macro_rules! regex {
    ($re:expr) => { regex::Regex::new($re).unwrap() }
}

fn main() {
    // let mut input = String::with_capacity(10 * 1024 * 1024);
    // io::stdin().read_to_string(&mut input).unwrap();
    // let input = include_str!("/tmp/regex-dna-input");
    let input = include_str!("/home/andrew/tmp/regex-dna.fasta");
    // let re = r">[^\n]*\n|\n";
    // let re = r"[ -~]*ABCDEFGHIJKLMNOPQRSTUVWXYZ$";
    // let re = "H";
    // let re = "agggtaaa|tttaccct";
    // let re = "[cgt]gggtaaa|tttaccc[acg]";
    // let re = "a[act]ggtaaa|tttacc[agt]t";
    // let re = regex::Regex::new(re).unwrap();
    // re.replace_all(&input, ::regex::NoExpand("(a|c|t)"));
    // re.replace_all(&input, ::regex::NoExpand(""));
    // println!("{}", re.find_iter(&input).count());

    let input = regex!(">[^\n]*\n|\n").replace_all(input, "");
    // let mut input = regex!(">[^\n]*\n").replace_all(input, "");
    // input = regex!("\n").replace_all(&input, "");
    println!("{}", input.len());
}
