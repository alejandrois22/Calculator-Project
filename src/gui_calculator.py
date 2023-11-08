import tkinter as tk

def perform_operation(operation):
    try:
        num1 = float(entry_num1.get())
        num2 = float(entry_num2.get())
        if operation == 'add':
            result.set(num1 + num2) 
        elif operation == 'subtract':
            result.set(num1 - num2)
        elif operation == 'multiply':
            result.set(num1 * num2)
        elif operation == 'divide':
            result.set(num1 / num2 if num2 != 0 else "Error: Division by zero")
    except ValueError:
        result.set("Please enter valid numbers")

def clear_entries():
    entry_num1.delete(0, tk.END)
    entry_num2.delete(0, tk.END)
    result.set("")

# Create the main window
root = tk.Tk()
root.title("Calculator")

# Variables for storing the entered numbers and the result
entry_num1 = tk.Entry(root)
entry_num2 = tk.Entry(root)
result = tk.StringVar()

# Layout the entry fields and result label
entry_num1.pack()
entry_num2.pack()
tk.Label(root, textvariable=result).pack()

# Layout the operation buttons
tk.Button(root, text="Add", command=lambda: perform_operation('add')).pack()
tk.Button(root, text="Subtract", command=lambda: perform_operation('subtract')).pack()
tk.Button(root, text="Multiply", command=lambda: perform_operation('multiply')).pack()
tk.Button(root, text="Divide", command=lambda: perform_operation('divide')).pack()

# Clear button to reset all fields
tk.Button(root, text="Clear", command=clear_entries).pack()

# Start the GUI loop
root.mainloop()
