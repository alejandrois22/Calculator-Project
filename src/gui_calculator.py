import tkinter as tk
import math
import re

# Function to append operator or number to the equation string
def append_to_equation(symbol):
    current_text = equation.get()
    if current_text == "Error":
        current_text = ""
    equation.set(current_text + symbol)

# Function to preprocess the equation and replace custom operators with python equivalents
def preprocess_equation(eq):
    # Insert * between a number and a sqrt symbol or power symbol
    eq = re.sub(r'(\d)([√^])', r'\1*\2', eq)
    
    # Replace the sqrt symbol with power of 0.5 for eval, capturing the operand following it
    eq = re.sub(r'√(\d+)', r'(\1)**0.5', eq)
    
    # Replace ^ with ** for exponentiation
    eq = eq.replace('^', '**')
    
    # Autocomplete missing parentheses
    open_parens, close_parens = eq.count('('), eq.count(')')
    eq += ')' * (open_parens - close_parens) if open_parens > close_parens else ''
    return eq

# Function to perform the calculation
def calculate():
    try:
        processed_equation = preprocess_equation(equation.get())
        result_text = str(eval(processed_equation))
        result_var.set(result_text)
        global last_answer
        last_answer = result_text
    except Exception as e:
        result_var.set("Error")

# Clear the current equation
def clear_all():
    equation.set("")
    result_var.set("")

# Delete the last character from the current equation
def backspace():
    equation.set(equation.get()[:-1])

# Use the last calculated answer
def use_last_answer():
    equation.set(str(last_answer))

# Main window setup
root = tk.Tk()
root.title("Calculator")

# StringVars for equation and result
equation = tk.StringVar()
result_var = tk.StringVar()
last_answer = 0

# Entry field for equation
entry_equation = tk.Entry(root, textvariable=equation, font=('Arial', 14))
entry_equation.pack(expand=True, fill='both')

# Entry field for result, set as read-only
entry_result = tk.Entry(root, textvariable=result_var, state='readonly', font=('Arial', 14))
entry_result.pack(expand=True, fill='both')

# Buttons for calculator
buttons = [
    ('(', ')', 'C', '/', '√'),
    ('7', '8', '9', '*', '^'),
    ('4', '5', '6', '-', '%'),
    ('1', '2', '3', '+', 'ANS'),
    ('0', '.', '=', '⌫')
]

# Function to create a button
def make_button(parent, text):
    return tk.Button(parent, text=text, font=('Arial', 14),
                     command=lambda: append_to_equation(text) if text not in ['=', 'C', '⌫', 'ANS'] else None)

# Add buttons to the UI
for row in buttons:
    frame = tk.Frame(root)
    for symbol in row:
        if symbol == '=':
            btn = make_button(frame, symbol)
            btn.config(command=calculate)
        elif symbol == 'C':
            btn = make_button(frame, symbol)
            btn.config(command=clear_all)
        elif symbol == '⌫':
            btn = make_button(frame, symbol)
            btn.config(command=backspace)
        elif symbol == 'ANS':
            btn = make_button(frame, symbol)
            btn.config(command=use_last_answer)
        else:
            btn = make_button(frame, symbol)
        btn.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

root.mainloop()
