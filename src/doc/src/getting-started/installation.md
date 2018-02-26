## Installation

### Install Rust and Cargo

The easiest way to get Cargo is to install the current stable release of [Rust]
by using `rustup`.

On Linux and macOS systems, this is done as follows:

```console
$ curl -sSf https://static.rust-lang.org/rustup.sh | sh
```

It will download a script, and start the installation. If everything goes well,
you’ll see this appear:

```console
Rust is installed now. Great! 
```

On Windows, download and run [rustup-init.exe]. It will start the installation
in a console and present the above message on success.

After this, you can use the `rustup` command to also install `beta` or `nightly`
channels for Rust and Cargo.

For other installation options and information, visit the
[install][install-rust] page of the Rust website.

### Build and Install Cargo from Source

Alternatively, you can [build Cargo from source][compiling-from-source].

[rust]: https://www.rust-lang.org/
[rustup-init.exe]: https://win.rustup.rs/
[install-rust]: https://www.rust-lang.org/install.html
[compiling-from-source]: https://github.com/rust-lang/cargo#compiling-from-source