# Gradio v6 Migration Notes

## Overview

Based on analysis of `src/generative_ai_toolkit/ui`, here are the changes required to make the code compatible with Gradio v6.

---

## 🔴 **CRITICAL CHANGES REQUIRED**

### 1. **Textbox Button Parameters** (4 changes in `ui.py`)

The `submit_btn` and `stop_btn` parameters must be replaced with the `buttons` parameter.

#### **Line 401** - Textbox initialization
```python
# CURRENT:
msg = gr.Textbox(
    placeholder="Type your message ...",
    submit_btn=True,
    autofocus=True,
    show_label=False,
    elem_id="user-input",
    interactive=False,
)

# CHANGE TO:
msg = gr.Textbox(
    placeholder="Type your message ...",
    buttons=["submit"],
    autofocus=True,
    show_label=False,
    elem_id="user-input",
    interactive=False,
)
```

#### **Line 96** - user_submit function
```python
# CURRENT:
return (
    gr.update(
        value="", interactive=False, submit_btn=False, stop_btn=True
    ),
    ...
)

# CHANGE TO:
return (
    gr.update(
        value="", interactive=False, buttons=["stop"]
    ),
    ...
)
```

#### **Line 132** - user_stop function
```python
# CURRENT:
return gr.update(stop_btn=False)

# CHANGE TO:
return gr.update(buttons=[])
```

#### **Line 668** - Re-enabling input
```python
# CURRENT:
lambda: gr.update(interactive=True, submit_btn=True, stop_btn=False),

# CHANGE TO:
lambda: gr.update(interactive=True, buttons=["submit"]),
```

---

## 🟡 **IMPORTANT CHANGES REQUIRED**

### 2. **App Parameters Moved from Blocks() to launch()** (3 changes in `ui.py`)

Parameters like `theme`, `css`, and `title` must be moved from `gr.Blocks()` to `demo.launch()`.

#### **Line 292** - chat_ui() function
```python
# CURRENT:
with gr.Blocks(
    theme="origin",
    fill_width=True,
    title=title,
    css="""
        .centered-row {
          align-items: center !important;
        }
        """,
) as demo:

# CHANGE TO:
with gr.Blocks(fill_width=True) as demo:
    # ... all the UI code ...

# Then when launching (in caller code):
demo.launch(
    theme="origin",
    title=title,
    css="""
        .centered-row {
          align-items: center !important;
        }
        """
)
```

#### **Line 819** - traces_ui() function
```python
# CURRENT:
with gr.Blocks(
    theme="origin", fill_width=True, title="Generative AI Toolkit"
) as demo:

# CHANGE TO:
with gr.Blocks(fill_width=True) as demo:
    # ... all the UI code ...

# Then when launching:
demo.launch(
    theme="origin",
    title="Generative AI Toolkit"
)
```

#### **Line 874** - measurements_ui() function
```python
# CURRENT:
with gr.Blocks(
    theme="origin", css=css, fill_width=True, title="Generative AI Toolkit"
) as demo:

# CHANGE TO:
with gr.Blocks(fill_width=True) as demo:
    # ... all the UI code ...

# Then when launching:
demo.launch(
    theme="origin",
    css=css,
    title="Generative AI Toolkit"
)
```

---

## ✅ **NO CHANGES NEEDED**

### 3. **Chatbot Components** 
- ✅ All `gr.Chatbot()` instances already use `type="messages"` (lines 441, 832, 1040)
- ✅ Messages use proper structured format (`gr.MessageDict` / `gr.ChatMessage`)
- ✅ No tuple format found anywhere
- ✅ No deprecated `show_copy_button` or similar parameters
- ✅ No `resizeable` typo

### 4. **Event Listeners**
- ✅ No usage of deprecated `show_api` parameter
- ✅ No usage of deprecated `api_name=False`
- ✅ All event listener parameters are v6-compatible

### 5. **Other Components**
- ✅ `gr.Timer` - No changes needed
- ✅ `gr.State` / `gr.BrowserState` - No changes needed
- ✅ `gr.Dropdown` - No deprecated parameters
- ✅ `gr.Button` - No deprecated parameters
- ✅ `gr.Markdown` - No deprecated parameters
- ✅ `gr.HTML` - Not used in the codebase

### 6. **Other Migration Topics**
- ✅ No `gr.Interface` or `gr.ChatInterface` usage
- ✅ No `Chatbot.like()` method usage
- ✅ No `gr.Video` usage
- ✅ No `gr.Dataframe` usage
- ✅ No `gr.ImageEditor` usage
- ✅ No webcam-related code

---

## 📋 **Summary by File**

### **src/generative_ai_toolkit/ui/ui.py**
- **7 changes required** (4 critical + 3 important)
  - Lines 96, 132, 401, 668: Button parameter changes (CRITICAL)
  - Lines 292, 819, 874: Move theme/css/title to launch() (IMPORTANT)

### **src/generative_ai_toolkit/ui/lib.py**
- **0 changes required** ✅

### **src/generative_ai_toolkit/ui/conversation_list/**
- **0 changes required** ✅

---

## 🎯 **Migration Priority**

1. **High Priority (Breaking)**: Fix Textbox button parameters (4 changes)
2. **Medium Priority (Breaking)**: Move Blocks() parameters to launch() (3 changes)
3. **Documentation**: Update any caller code to pass theme/css/title to launch()

---

## ⚠️ **Important Note**

Since the UI functions (`chat_ui()`, `traces_ui()`, `measurements_ui()`) return the `demo` object without calling `.launch()`, the caller code will need to be updated to pass the appropriate parameters to `.launch()`. Check all places where these functions are called.

---

**Total changes needed: 7 changes in `ui.py`**
