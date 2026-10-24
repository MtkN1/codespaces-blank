"""typing.Protocol 入門: 「形が合えば使える」という考え方。"""

from typing import Protocol, runtime_checkable


# --8<-- [start:protocol]
@runtime_checkable
class Speaker(Protocol):
    """「話せるもの」の約束。継承は不要で、形 (メソッド) が合えば OK。"""

    def speak(self, text: str) -> str: ...
# --8<-- [end:protocol]


# --8<-- [start:impls]
class Dog:  # Speaker を継承していない
    def speak(self, text: str) -> str:
        return f"ワン! ({text})"


class Robot:  # こちらも継承していない
    def speak(self, text: str) -> str:
        return f"[beep] {text}"


class Stone:  # speak を持たない
    pass
# --8<-- [end:impls]


# --8<-- [start:use]
def greet(s: Speaker) -> str:
    # 相手が何者かは知らない。知っているのは「speak できる」ことだけ。
    return s.speak("こんにちは")


print(greet(Dog()))    # ワン! (こんにちは)
print(greet(Robot()))  # [beep] こんにちは
# greet(Stone())       # ← mypy / pyright がエラーにしてくれる

print(isinstance(Stone(), Speaker))  # False (runtime_checkable なら実行時にも確認可)
# --8<-- [end:use]
