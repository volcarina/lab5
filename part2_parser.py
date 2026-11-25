import re
import sys


# Допустимые символы для имен переменных (1-2 символа), не пересекающиеся с римскими цифрами l, x, v, i
VAR_FIRST_CHARS = set("abcdefghjkmnopqrstuwyz")
VAR_SECOND_CHARS = VAR_FIRST_CHARS | set("0123456789")
ROMAN_CHARS = set("lxvi")
ROMAN_RE = re.compile(r"^(l(x{0,3})|x(l|x{0,2}))?(v(i{0,3})|i(x|v|i{0,2}))?$")


class LexError(Exception):
    pass


class ParseError(Exception):
    pass


def tokenize(text: str):
    """Лексический анализатор для варианта 12 (Часть 2)."""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\r":
            i += 1
            continue
        if ch == "\n":
            tokens.append((";", ";"))
            i += 1
            continue
        if ch in "+-*/=();":
            tokens.append((ch, ch))
            i += 1
            continue
        if ch.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            lex = text[i:j]
            if (len(lex) > 1 and lex[0] == "0") or (j < n and text[j].isalpha()):
                raise LexError(f"Некорректная десятичная константа: {lex}")
            tokens.append(("int", lex))
            i = j
            continue
        if ch in ROMAN_CHARS:
            j = i
            while j < n and text[j].isalnum():
                j += 1
            lex = text[i:j]
            if not lex or not all(c in ROMAN_CHARS for c in lex) or not ROMAN_RE.match(lex):
                raise LexError(f"Некорректное римское число: {lex}")
            tokens.append(("roman", lex))
            i = j
            continue
        if ch in VAR_FIRST_CHARS:
            j = i
            while j < n and text[j].isalnum():
                j += 1
            lex = text[i:j]
            if len(lex) > 2:
                raise LexError(f"Слишком длинное имя переменной (допустимо 1-2 символа): {lex}")
            if len(lex) == 2 and lex[1] not in VAR_SECOND_CHARS:
                raise LexError(f"Недопустимый второй символ в имени переменной: {lex}")
            tokens.append(("id", lex))
            i = j
            continue
        raise LexError(f"Недопустимый символ: {ch!r}")
    tokens.append(("$", "$"))
    return tokens


class RecursiveDescentParser:
    """
    Синтаксический анализатор методом рекурсивного спуска для LL(1)-грамматики
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos][0]

    def match(self, expected):
        if self.peek() == expected:
            self.pos += 1
        else:
            raise ParseError(f"Ожидался токен {expected}, получен {self.peek()}")

    def parse(self):
        self.parse_S()
        if self.peek() != "$":
            raise ParseError(f"Лишние символы в конце входа: {self.peek()}")

    def parse_S(self):
        self.parse_E()
        self.parse_S_prime()

    def parse_S_prime(self):
        if self.peek() == ";":
            self.match(";")
            self.parse_E()
            self.parse_S_prime()
        elif self.peek() == "$":
            return  # ε
        else:
            raise ParseError(f"Неожиданный токен в S': {self.peek()}")

    def parse_E(self):
        tok = self.peek()
        if tok == "id":
            self.match("id")
            self.parse_E_id()
        elif tok in ("-", "+", "(", "roman", "int"):
            self.parse_U_nonid()
            self.parse_G()
        else:
            raise ParseError(f"Неожиданный токен в начале выражения E: {tok}")

    def parse_E_id(self):
        tok = self.peek()
        if tok == "=":
            self.match("=")
            self.parse_E()
        elif tok in ("+", "-", "*", "/", ")", ";", "$"):
            self.parse_G()
        else:
            raise ParseError(f"Неожиданный токен после идентификатора: {tok}")

    def parse_U_nonid(self):
        tok = self.peek()
        if tok == "-":
            self.match("-")
            self.parse_U()
        elif tok == "+":
            self.match("+")
            self.parse_U()
        elif tok == "(":
            self.match("(")
            self.parse_E()
            self.match(")")
        elif tok == "roman":
            self.match("roman")
        elif tok == "int":
            self.match("int")
        else:
            raise ParseError(f"Неожиданный токен в U_nonid: {tok}")

    def parse_U(self):
        tok = self.peek()
        if tok == "-":
            self.match("-")
            self.parse_U()
        elif tok == "+":
            self.match("+")
            self.parse_U()
        elif tok in ("(", "id", "roman", "int"):
            self.parse_F()
        else:
            raise ParseError(f"Неожиданный токен в U: {tok}")

    def parse_F(self):
        tok = self.peek()
        if tok == "(":
            self.match("(")
            self.parse_E()
            self.match(")")
        elif tok == "id":
            self.match("id")
        elif tok == "roman":
            self.match("roman")
        elif tok == "int":
            self.match("int")
        else:
            raise ParseError(f"Неожиданный токен в F: {tok}")

    def parse_G(self):
        tok = self.peek()
        if tok in ("+", "-", "*", "/"):
            self.parse_B()
            self.parse_U()
            self.parse_G()
        elif tok in (")", ";", "$"):
            return  # ε
        else:
            raise ParseError(f"Неожиданный токен в G: {tok}")

    def parse_B(self):
        tok = self.peek()
        if tok in ("+", "-", "*", "/"):
            self.match(tok)
        else:
            raise ParseError(f"Ожидалась бинарная операция, получено: {tok}")


def analyze(expression: str) -> str:
    try:
        tokens = tokenize(expression)
        parser = RecursiveDescentParser(tokens)
        parser.parse()
        return "Accepted"
    except (LexError, ParseError):
        return "Rejected"


if __name__ == "__main__":
    tests = [
        ("a=xv+10", "Accepted"),
        ("ab=-iv*(c1+25)", "Accepted"),
        ("a=b=lxxxix", "Accepted"),
        ("k1=0;m2=k1+xliv;m2*2", "Accepted"),
        ("-(a1+ix)/3", "Accepted"),
        ("a+(b=v)*ii", "Accepted"),
        ("+x-(-12)+d", "Accepted"),
        ("a+b=10", "Rejected"),
        ("15=a", "Rejected"),
        ("abc=v", "Rejected"),
        ("a=iiii", "Rejected"),
        ("a=012", "Rejected"),
        ("a=(x+v", "Rejected"),
        ("a=v;", "Rejected"),
    ]
    print("=== Тестирование синтаксического анализатора ===")
    all_ok = True
    for expr, expected in tests:
        res = analyze(expr)
        ok = (res == expected)
        all_ok = all_ok and ok
        print(f"  {expr:26s} -> {res:8s} (ожидалось: {expected})")
    print("Все тесты пройдены:" , all_ok)
    if sys.stdin.isatty():
        while True:
            s = input("\nВведите строку для анализа (Enter для выхода): ").strip()
            if not s:
                break
            print("Результат:", analyze(s))
