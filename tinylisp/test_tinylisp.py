import unittest
from tinylisp import LispError, run, to_string


class T(unittest.TestCase):
    def ev(self, s):
        return to_string(run(s))

    def test_arith(self):
        self.assertEqual(self.ev("(+ 1 2 (* 3 4))"), "15")
        self.assertEqual(self.ev("(- 5)"), "-5")
        self.assertEqual(self.ev("(/ 10 4)"), "2.5")
        self.assertEqual(self.ev("(/ 10 5)"), "2")

    def test_closures(self):
        self.assertEqual(self.ev(
            "(define (adder n) (lambda (x) (+ x n))) ((adder 3) 4)"), "7")
        self.assertEqual(self.ev(
            "(define (counter) (let ((n 0)) (lambda () (set! n (+ n 1)) n)))"
            "(define c (counter)) (c) (c) (c)"), "3")

    def test_tail_calls_do_not_overflow(self):
        self.assertEqual(self.ev(
            "(define (loop n acc) (if (= n 0) acc (loop (- n 1) (+ acc 1))))"
            "(loop 200000 0)"), "200000")

    def test_mutual_tail_calls(self):
        self.assertEqual(self.ev(
            "(define (ev? n) (if (= n 0) #t (od? (- n 1))))"
            "(define (od? n) (if (= n 0) #f (ev? (- n 1))))"
            "(ev? 100001)"), "#f")

    def test_lists(self):
        self.assertEqual(self.ev("(cons 1 '(2 3))"), "(1 2 3)")
        self.assertEqual(self.ev("(append '(1) '(2 3) '())"), "(1 2 3)")
        self.assertEqual(self.ev("(null? (cdr '(1)))"), "#t")

    def test_higher_order(self):
        self.assertEqual(self.ev("""
            (define (map f l) (if (null? l) '() (cons (f (car l)) (map f (cdr l)))))
            (map (lambda (x) (* x x)) '(1 2 3 4))"""), "(1 4 9 16)")

    def test_cond_and_or(self):
        self.assertEqual(self.ev("(cond ((< 3 2) 1) ((> 3 2) 2) (else 3))"), "2")
        self.assertEqual(self.ev("(and 1 2 3)"), "3")
        self.assertEqual(self.ev("(or #f #f 7)"), "7")
        self.assertEqual(self.ev("(and)"), "#t")

    def test_zero_is_truthy(self):
        self.assertEqual(self.ev("(if 0 'yes 'no)"), "yes")

    def test_strings(self):
        self.assertEqual(self.ev('(string-append "a" "b")'), '"ab"')

    def test_errors(self):
        for bad in ("(foo)", "(/ 1 0)", "((lambda (x) x))", "(1 2)", "(car)", "(", ")"):
            with self.assertRaises(LispError, msg=bad):
                run(bad)

    def test_fib(self):
        self.assertEqual(self.ev(
            "(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2))))) (fib 15)"), "610")


if __name__ == "__main__":
    unittest.main()
