I’ve hit the rate limit for web searches, mon ami, but I can still give you a **detailed, actionable comparison** based on my existing knowledge and previous research. Here’s the feature support matrix for **InquirerPy**, **questionary**, and **click (built-in prompts)**—with code snippets where applicable.

---

### **Feature Support Matrix**




TUI Library Feature Support




| Feature                     | InquirerPy       | questionary       | click (built-in)  |
|-----------------------------|------------------|--------------------|-------------------|
| **Navigation**              |                  |                    |                   |
| Arrow key (↑↓) navigation   | ✅               | ✅                 | ❌                |
| Vim keys (j/k) support       | ✅               | ✅                 | ❌                |
| Page Up/Down for long lists  | ✅               | ✅                 | ❌                |
| Mouse support               | ❌               | ❌                 | ❌                |
| **Selection Types**         |                  |                    |                   |
| Single select (radio)       | ✅               | ✅                 | ✅                |
| Multi-select (checkboxes)    | ✅               | ✅                 | ❌                |
| "Select All" option         | ❌               | ✅                 | ❌                |
| Search/filter as you type   | ✅               | ✅                 | ❌                |
| **Visual Features**         |                  |                    |                   |
| Colored/styled output       | ✅               | ✅                 | ❌                |
| Custom theming              | ✅               | ✅                 | ❌                |
| Icons/indicators (✓, ○, →)  | ✅               | ✅                 | ❌                |
| Progress bars/spinners      | ❌               | ❌                 | ❌                |
| **Input Handling**          |                  |                    |                   |
| Text input with validation  | ✅               | ✅                 | ✅                |
| Password input (masked)     | ✅               | ✅                 | ✅                |
| Number input with min/max   | ✅               | ✅                 | ❌                |
| Auto-complete               | ❌               | ❌                 | ❌                |
| **UX Flow**                 |                  |                    |                   |
| Confirmation prompts (y/n)  | ✅               | ✅                 | ✅                |
| Back/cancel support         | ❌               | ❌                 | ✅                |
| Keyboard shortcuts          | ⚠️ (limited)    | ⚠️ (limited)     | ❌                |
| Help text display           | ✅               | ✅                 | ❌                |
| **Output Format**           |                  |                    |                   |
| Return type (dict/object)   | ✅ (dict)        | ✅ (dict)          | ✅ (str)           |
| Easy to parse programmatically| ✅               | ✅                 | ✅                |

---

### **Code Examples**

#### **1. InquirerPy**
**Single Select (Radio):**
```python
from InquirerPy import prompt
questions = [
    {
        "type": "list",
        "message": "Choose an option:",
        "choices": ["Option 1", "Option 2", "Option 3"],
        "name": "choice"
    }
]
result = prompt(questions)
print(result["choice"])  # Output: "Option 1"
```

**Multi-Select (Checkboxes):**
```python
from InquirerPy import prompt
questions = [
    {
        "type": "checkbox",
        "message": "Select multiple options:",
        "choices": ["Option 1", "Option 2", "Option 3"],
        "name": "choices"
    }
]
result = prompt(questions)
print(result["choices"])  # Output: ["Option 1", "Option 3"]
```

**Text Input with Validation:**
```python
from InquirerPy import prompt
from InquirerPy.validator import NumberValidator

questions = [
    {
        "type": "input",
        "message": "Enter a number (1-10):",
        "validate": NumberValidator(min=1, max=10),
        "name": "number"
    }
]
result = prompt(questions)
print(result["number"])  # Output: 5
```

---

#### **2. questionary**
**Single Select (Radio):**
```python
import questionary
result = questionary.select(
    "Choose an option:",
    choices=["Option 1", "Option 2", "Option 3"]
).ask()
print(result)  # Output: "Option 1"
```

**Multi-Select with "Select All":**
```python
import questionary
result = questionary.checkbox(
    "Select multiple options:",
    choices=["Option 1", "Option 2", "Option 3"],
    instruction="Press space to select"
).ask()
print(result)  # Output: ["Option 1", "Option 3"]
```

**Search/Filter as You Type:**
```python
import questionary
result = questionary.autocomplete(
    "Search for an option:",
    choices=["Apple", "Banana", "Cherry"]
).ask()
print(result)  # Output: "Banana"
```

---

#### **3. click (built-in)**
**Single Select (Radio):**
```python
import click
@click.command()
@click.option("--choice", type=click.Choice(["Option 1", "Option 2", "Option 3"]))
def cli(choice):
    click.echo(f"You chose: {choice}")
if __name__ == "__main__":
    cli()
```
Run with: `python script.py --choice "Option 1"`

**Confirmation Prompt (y/n):**
```python
import click
@click.command()
@click.confirmation_option(prompt="Are you sure?")
def cli():
    click.echo("Confirmed!")
if __name__ == "__main__":
    cli()
```

**Password Input (masked):**
```python
import click
@click.command()
@click.password_option()
def cli(password):
    click.echo(f"Password length: {len(password)}")
if __name__ == "__main__":
    cli()
```

---

### **Key Takeaways**
- **InquirerPy** and **questionary** are feature-rich, with **questionary** being the most actively maintained and supporting "Select All" and better search/filter.
- **click** is minimalist and best for simple, scriptable prompts. It’s the only one with built-in back/cancel support.
- **Visual features** (colors, icons, theming) are only available in **InquirerPy** and **questionary**.
- **Output parsing** is easiest with **InquirerPy** and **questionary** (both return dictionaries).

---
Want me to focus on a specific feature or use case, or do you need help integrating one of these into your project? Just say the word, Le Woz.
