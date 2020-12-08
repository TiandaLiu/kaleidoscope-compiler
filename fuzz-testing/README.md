# Fuzz Testing

## Usage
put sample file into inputs folder first, then run:

    py-afl-fuzz -m 400 -i inputs/ -o outputs/ -- python3 fuzz-wrapper.py

## Requirement:
    brew install afl-fuzz
    pip install python-afl

## References:
    https://alexgaynor.net/2015/apr/13/introduction-to-fuzzing-in-python-with-afl/
    https://barro.github.io/2018/01/taking-a-look-at-python-afl/