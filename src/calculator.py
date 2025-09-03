import math
import json
import os
import re
from typing import Any, Callable, Dict, List, Tuple, Union


Number = Union[int, float, complex]


class CalculatorEngine:
    """
    Core calculator engine providing:
    - Safe expression evaluation with scientific functions
    - Memory operations (MC, MR, M+, M-)
    - Calculation history and last answer (ANS)
    - Session persistence (history, memory, last_answer)
    """

    def __init__(self) -> None:
        self.memory_value: Number = 0
        self.last_answer: Number = 0
        self.history: List[Tuple[str, str]] = []  # (expression, result)
        self._session_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", ".calculator_session.json"
        )
        # User-defined functions mapping: name -> callable
        self.user_functions: Dict[str, Callable[..., Number]] = {}
        self.load_session()

    # ----------------------------- Session ---------------------------------
    def save_session(self) -> None:
        try:
            data = {
                "memory_value": self._serialize_number(self.memory_value),
                "last_answer": self._serialize_number(self.last_answer),
                "history": [(expr, res) for expr, res in self.history[-200:]],
            }
            with open(self._session_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Best-effort persistence; ignore errors
            pass

    def load_session(self) -> None:
        try:
            if os.path.exists(self._session_file_path):
                with open(self._session_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.memory_value = self._deserialize_number(data.get("memory_value", 0))
                self.last_answer = self._deserialize_number(data.get("last_answer", 0))
                self.history = list(data.get("history", []))
        except Exception:
            # Ignore broken session files
            self.memory_value = 0
            self.last_answer = 0
            self.history = []

    # ----------------------------- Memory ----------------------------------
    def memory_clear(self) -> None:
        self.memory_value = 0

    def memory_recall(self) -> Number:
        return self.memory_value

    def memory_add(self, value: Number) -> Number:
        self.memory_value = self._coerce_number(self.memory_value + value)
        return self.memory_value

    def memory_subtract(self, value: Number) -> Number:
        self.memory_value = self._coerce_number(self.memory_value - value)
        return self.memory_value

    # ----------------------------- Evaluate --------------------------------
    def evaluate(self, expression: str) -> str:
        """Evaluate an expression and return a string result or error message."""
        cleaned = self._preprocess_expression(expression)
        try:
            allowed = self._allowed_names()
            # Restrict builtins
            result: Number = eval(cleaned, {"__builtins__": {}}, allowed)  # noqa: S307
            result = self._coerce_number(result)
            result_str = self._format_result(result)
            self.last_answer = result
            self._append_history(expression, result_str)
            return result_str
        except ZeroDivisionError:
            return "Error: Division by zero"
        except ValueError as ve:
            return f"Error: {ve}"
        except OverflowError:
            return "Error: Number too large"
        except Exception as ex:  # catch-all for syntax/math errors
            return f"Error: {type(ex).__name__}"

    # ----------------------------- Helpers ---------------------------------
    def _append_history(self, expr: str, result_str: str) -> None:
        self.history.append((expr, result_str))
        # Trim history to a reasonable size
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    @staticmethod
    def _format_result(value: Number) -> str:
        if isinstance(value, complex):
            # Normalize very small parts to zero for readability
            real = 0.0 if abs(value.real) < 1e-12 else value.real
            imag = 0.0 if abs(value.imag) < 1e-12 else value.imag
            value = complex(real, imag)
            return str(value)
        # For floats, strip trailing zeros
        if isinstance(value, float):
            return ("%.*g" % (15, value)).rstrip(".0").rstrip(".") if value != int(value) else str(int(value))
        return str(value)

    @staticmethod
    def _coerce_number(value: Any) -> Number:
        # Accept int/float/complex; raise for other types
        if isinstance(value, (int, float, complex)):
            return value
        raise ValueError("Unsupported result type")

    @staticmethod
    def _serialize_number(value: Number) -> Union[float, Dict[str, float]]:
        if isinstance(value, complex):
            return {"real": value.real, "imag": value.imag}
        return float(value)

    @staticmethod
    def _deserialize_number(value: Union[float, Dict[str, float], None]) -> Number:
        if isinstance(value, dict) and "real" in value and "imag" in value:
            return complex(value["real"], value["imag"])
        try:
            return float(value) if value is not None else 0.0
        except Exception:
            return 0.0

    def _preprocess_expression(self, expr: str) -> str:
        if expr is None:
            return ""
        s = str(expr).strip()
        # Replace UI symbols
        s = s.replace("×", "*").replace("÷", "/")
        s = s.replace("^", "**")
        # Replace ANS token with last answer
        s = re.sub(r"\bANS\b", f"({self.last_answer})", s)
        # Support simple percentage postfix (e.g., 50%)
        s = re.sub(r"(?<!\w)(\d+(?:\.\d+)?)%", r"(\1/100)", s)
        # Allow imaginary unit i/I
        s = re.sub(r"\b([iI])\b", "(1j)", s)
        # Implicit multiplication: number followed by ( or variable/function
        s = re.sub(r"(\d)(\()", r"\1*\2", s)
        s = re.sub(r"(\))(\d)", r"\1*\2", s)
        s = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", s)
        return s

    # -------------------------- Allowed namespace --------------------------
    def _allowed_names(self) -> Dict[str, Any]:
        # Trig in degrees for sin/cos/tan; inverse trig returns degrees
        def sin_deg(x: Number) -> float:
            return math.sin(math.radians(float(x)))

        def cos_deg(x: Number) -> float:
            return math.cos(math.radians(float(x)))

        def tan_deg(x: Number) -> float:
            return math.tan(math.radians(float(x)))

        def asin_deg(x: Number) -> float:
            return math.degrees(math.asin(float(x)))

        def acos_deg(x: Number) -> float:
            return math.degrees(math.acos(float(x)))

        def atan_deg(x: Number) -> float:
            return math.degrees(math.atan(float(x)))

        def ln(x: Number) -> float:
            return math.log(float(x))

        def log(x: Number) -> float:  # base-10
            return math.log10(float(x))

        def sqrt(x: Number) -> Number:
            if isinstance(x, (int, float)) and x < 0:
                # allow complex sqrt
                return complex(0, math.sqrt(abs(float(x))))
            return math.sqrt(float(x))

        def factorial(n: Number) -> int:
            n_float = float(n)
            if not n_float.is_integer() or n_float < 0:
                raise ValueError("factorial() only defined for non-negative integers")
            return math.factorial(int(n_float))

        def to_rad(x: Number) -> float:
            return math.radians(float(x))

        def to_deg(x: Number) -> float:
            return math.degrees(float(x))

        # Unit conversion
        def convert(value: Number, from_unit: str, to_unit: str) -> float:
            return self._convert_units(float(value), str(from_unit), str(to_unit))

        allowed: Dict[str, Any] = {
            # constants
            "pi": math.pi,
            "e": math.e,
            "ANS": self.last_answer,
            # trig/log
            "sin": sin_deg,
            "cos": cos_deg,
            "tan": tan_deg,
            "asin": asin_deg,
            "acos": acos_deg,
            "atan": atan_deg,
            "ln": ln,
            "log": log,
            "sqrt": sqrt,
            "factorial": factorial,
            "rad": to_rad,
            "deg": to_deg,
            # memory convenience
            "MR": lambda: self.memory_recall(),
            # conversions
            "convert": convert,
            # built-in safe functions
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
        }

        # Expose user-defined functions (if any)
        allowed.update(self.user_functions)
        return allowed

    # --------------------------- Unit conversion ---------------------------
    def _convert_units(self, value: float, from_unit: str, to_unit: str) -> float:
        length_in_m = {
            "m": 1.0,
            "meter": 1.0,
            "meters": 1.0,
            "km": 1000.0,
            "kilometer": 1000.0,
            "kilometers": 1000.0,
            "cm": 0.01,
            "mm": 0.001,
            "mi": 1609.344,
            "mile": 1609.344,
            "miles": 1609.344,
            "yd": 0.9144,
            "yard": 0.9144,
            "ft": 0.3048,
            "foot": 0.3048,
            "feet": 0.3048,
            "in": 0.0254,
            "inch": 0.0254,
            "inches": 0.0254,
        }
        weight_in_kg = {
            "kg": 1.0,
            "kilogram": 1.0,
            "kilograms": 1.0,
            "g": 0.001,
            "gram": 0.001,
            "grams": 0.001,
            "lb": 0.45359237,
            "pound": 0.45359237,
            "pounds": 0.45359237,
            "oz": 0.028349523125,
            "ounce": 0.028349523125,
            "ounces": 0.028349523125,
        }
        volume_in_l = {
            "l": 1.0,
            "liter": 1.0,
            "liters": 1.0,
            "ml": 0.001,
            "milliliter": 0.001,
            "gallon": 3.785411784,
            "gallons": 3.785411784,
            "gal": 3.785411784,
        }

        def convert_through_base(v: float, table: Dict[str, float], src: str, dst: str) -> float:
            if src not in table or dst not in table:
                raise ValueError("Unsupported unit")
            return v * table[src] / table[dst]

        src = from_unit.lower()
        dst = to_unit.lower()
        if src in length_in_m and dst in length_in_m:
            return convert_through_base(value, length_in_m, src, dst)
        if src in weight_in_kg and dst in weight_in_kg:
            return convert_through_base(value, weight_in_kg, src, dst)
        if src in volume_in_l and dst in volume_in_l:
            return convert_through_base(value, volume_in_l, src, dst)
        raise ValueError("Incompatible or unsupported units")


__all__ = ["CalculatorEngine"]

