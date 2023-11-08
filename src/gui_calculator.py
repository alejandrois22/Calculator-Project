import tkinter as tk
import re

def append_to_equation(symbol):
    # Append the operator or number to the equation string
    current_text = equation.get()
    if current_text == "Error":
        current_text = ""
    equation.set(current_text + symbol)

def preprocess_equation(eq):
    # Insert * between a number and a parenthesis
    eq = re.sub(r'(\d)\(', r'\1*(', eq)
    eq = re.sub(r'\)(\d)', r')*\1', eq)
    # Autocomplete missing parentheses
    open_parens, close_parens = eq.count('('), eq.count(')')
    eq += ')' * (open_parens - close_parens) if open_parens > close_parens else ''
    return eq

def calculate():
    try:
        # Preprocess the equation and evaluate
        processed_equation = preprocess_equation(equation.get())
        result_text = str(eval(processed_equation))
        result.set(result_text)
    except (ValueError, ZeroDivisionError, SyntaxError):
        # Handle common errors from invalid equations
        result.set("Error")

def clear_all():
    equation.set("")
    result.set("")

def backspace():
    # Remove the last character from the equation string
    equation.set(equation.get()[:-1])

# Create the main window
root = tk.Tk()
root.title("Calculator")
root.geometry("300x300")  # Default size

# StringVars for storing the equation and result
equation = tk.StringVar()
result = tk.StringVar()

# Entry field for the equation
entry_equation = tk.Entry(root, textvariable=equation, state='normal', font=('Arial', 14))
entry_equation.pack(expand=True, fill='both')

# Entry field for the result, set to read-only
entry_result = tk.Entry(root, textvariable=result, state='readonly', font=('Arial', 14))
entry_result.pack(expand=True, fill='both')

# Buttons for numbers, operations, and parentheses
buttons = [
    ('(', ')', 'C', '/'),
    ('7', '8', '9', '*'),
    ('4', '5', '6', '-'),
    ('1', '2', '3', '+'),
    ('0', '.', '=', '⌫')  # Using the backspace symbol '⌫'
]

for row in buttons:
    frame = tk.Frame(root)
    for symbol in row:
        btn = tk.Button(frame, text=symbol, font=('Arial', 14),
                        command=lambda sym=symbol: append_to_equation(sym) if sym not in ['=', 'C', '⌫'] else None)
        if symbol == '=':
            btn.config(command=calculate)
        elif symbol == 'C':
            btn.config(command=clear_all)
        elif symbol == '⌫':
            btn.config(command=backspace)
        btn.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

# Adjust the size of the buttons as the window resizes
def resize_buttons(event):
    size = max(min(event.width, event.height) // 15, 8)
    font = ('Arial', size)
    for widget in root.winfo_children():
        if isinstance(widget, tk.Button) or isinstance(widget, tk.Entry):
            widget.config(font=font)

root.bind('<Configure>', resize_buttons)

# Start the GUI loop
root.mainloop()
