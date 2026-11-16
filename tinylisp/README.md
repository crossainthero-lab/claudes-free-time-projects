# tinylisp

A small Scheme-flavoured Lisp. One file, no dependencies.

```sh
python3 tinylisp.py                      # REPL
python3 tinylisp.py examples/primes.lisp # run a file
python3 -m unittest -q                   # tests
```

```lisp
lisp> (define (fact n) (if (< n 2) 1 (* n (fact (- n 1)))))
lisp> (fact 20)
2432902008176640000
lisp> (define (adder n) (lambda (x) (+ x n)))
lisp> ((adder 3) 4)
7
```

**Special forms:** `quote` (`'`), `if`, `cond`, `define` (including `(define (f x) ...)`), `set!`, `lambda`, `let`, `begin`, `and`, `or`.
**Builtins:** arithmetic and comparisons, `cons car cdr list append length null? list? number? symbol?`, `string-append`, `display`, `newline`.

**Tail calls** are eliminated in `if`, `cond`, `let`, `begin`, `and`, `or` and function application, so loops of any depth run in constant Python stack (the tests run 200,000 iterations and mutual recursion 100,001 deep).

**Deliberate simplifications:** only `#f` is false (so `0` and `()` are truthy, as in Scheme), lists are Python lists rather than cons cells, and `+` doesn't type-check strings. Errors surface as `LispError` instead of stack traces.
