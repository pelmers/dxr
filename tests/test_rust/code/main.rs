#[ crate_id = "test" ];

// A simple rust project

//extern mod crate2;
extern mod myextra = "extra";
//TODO doesn't work right now in rust
//extern mod core = "github.com/thestinger/rust-core/tree/master/core";

use msalias = sub::sub2;
use sub::sub2;
use myextra::arc;

static yy: uint = 25u;

static bob: Option<myextra::bigint::BigInt> = None;


mod sub {
    pub mod sub2 {
        pub mod sub3 {
          pub fn hello() {
              println("hello from module 3");
          }          
        }
        pub fn hello() {
            println("hello from a module");
        }

        pub struct nested_struct {
            field2: u32,
        }
    }

}

pub mod SameDir;
pub mod SubDir;

#[path = "SameDir3.rs"]
pub mod SameDir2;

struct nofields;
struct some_fields {
    field1: u32,
}

trait SuperTrait {
}

trait SomeTrait : SuperTrait {
    fn Method(&self, x: u32) -> u32;

    fn prov(&self, x: u32) -> u32 {
        println(x.to_str());
        42
    }  
    fn stat2(x: &Self) -> u32 {
        32
    }  
}

trait SubTrait: SomeTrait {
    fn provided_method(&self) -> u32 {
        42
    }
}

impl SomeTrait for some_fields {
    fn Method(&self, x: u32) -> u32 {
        println(x.to_str());
        self.field1
    }  
}

impl SuperTrait for some_fields {

}

impl some_fields {
    fn stat(x: u32) -> u32 {
        println(x.to_str());
        42
    }  
    fn stat2(x: &some_fields) -> u32 {
        42
    }  
}

impl SuperTrait for nofields {
}
impl SomeTrait for nofields {
    fn Method(&self, x: u32) -> u32 {
        43
    }    
}
impl SubTrait for nofields {
    fn provided_method(&self) -> u32 {
        21
    }
}

type MyType = ~some_fields;

fn f_with_params<T: SomeTrait>(x: &T) {
    x.Method(41);
}


fn hello((z, a) : (u32, ~str)) {
    SameDir2::hello(43);

    println(yy.to_str());
    let (x, y): (u32, u32) = (5, 3);
    println(x.to_str());
    println(z.to_str());
    let x: u32 = x;
    println(x.to_str());
    let x = ~"hello";
    println(x);

    let s: ~SomeTrait = ~some_fields {field1: 43};
    let s2: ~some_fields = ~some_fields {field1: 43};
    let s3 = ~nofields;

    s.Method(43);
    s3.Method(43);
    s2.Method(43);

    let y: u32 = 56;
    // static method on struct
    let r = some_fields::stat(y);
    // trait static method, calls override
    // TODO what is the syntax for this?
    let r = SomeTrait::stat2(s2);
    // trait static method, calls default
    let r = SomeTrait::stat2(s3);

    let s4 = s3 as ~SubTrait;
    s4.Method(43);
}

fn main() {
    hello((43, ~"a"));
    sub::sub2::hello();
    sub2::sub3::hello();

    let h = sub2::sub3::hello;
    h();

    let s1 = nofields;
    let s2 = some_fields{ field1: 55};
    let s3: some_fields = some_fields{ field1: 55};
    let s4: msalias::nested_struct = sub::sub2::nested_struct{ field2: 55};
    let s4: msalias::nested_struct = sub2::nested_struct{ field2: 55};
    println(s2.field1.to_str());
    let s5: MyType = ~some_fields{ field1: 55};

    let s = SameDir::SameStruct{name:~"Bob"};
    let s = SubDir::SubStruct{name:~"Bob"};
}
