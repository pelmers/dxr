// A simple rust project

use msalias = sub::sub2;
use sub::sub2;

static yy: uint = 25u;

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

struct nofields;
struct some_fields {
    field1: u32,
}

trait SuperTrait {

}

trait SomeTrait : SuperTrait {
    fn Method(&self, x: u32) -> u32;
}

trait SubTrait: SomeTrait {

}

impl SomeTrait for some_fields {
    fn Method(&self, x: u32) -> u32 {
        self.field1
    }  
}

impl SuperTrait for some_fields {

}

impl some_fields {

}

type MyType = ~some_fields;

enum SomeEnum {
    Ints(int, int),
    Floats(f64, f64),
    Strings(~str, ~str, ~str),
    MyTypes(MyType, MyType)
}

enum SomeOtherEnum {
    SomeConst1,
    SomeConst2,
    SomeConst3
}

fn matchSomeEnum(val : SomeEnum) {
    match val {
        Ints(int1, int2) => { println((int1+int2).to_str()); }
        Floats(float1, float2) => { println((float2*float1).to_str()); }
        Strings(_, _, s3) => { println(s3); }
        MyTypes(mt1, mt2) => { println((mt1.field1 - mt2.field1).to_str()); }
    }
}

fn hello((z, a) : (u32, ~str)) {
    println(yy.to_str());
    let (x, y): (u32, u32) = (5, 3);
    println(x.to_str());
    println(z.to_str());
    let x: u32 = x;
    println(x.to_str());
    let x = ~"hello";
    println(x);

    let s: ~SomeTrait = ~some_fields {field1: 43};
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
    let s6: SomeEnum = MyTypes(~s2, s5);
    let s7: SomeEnum = Strings(~"one",~"two",~"three");
    matchSomeEnum(s6);
    matchSomeEnum(s7);
}
