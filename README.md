# 🍳 Sangkap AI

Sangkap AI is an intelligent culinary assistant that helps you minimize food waste by generating delicious, structured recipes based on the ingredients you already have in your pantry. It uses Gemini 2.5 Flash for reasoning and recipe generation, ensures strict output formatting with Pydantic, and remembers your past recipes using Supabase.

## Features

**Core Recipe Generation**
*   **Pantry-First Approach:** Takes a list of raw ingredients you currently have and generates a practical, appetizing recipe prioritizing those items.
*   **Portion Control:** Customizes the recipe based on the desired number of people (1, 2, 3, or many) and estimates the exact number of servings.
*   **Detailed Measurements:** Automatically calculates and provides specific measurements for all used and missing ingredients.
*   **Smart Shopping List:** Identifies 1 to 3 critical missing ingredients to buy to significantly improve the dish.
*   **Comprehensive Details:** Provides step-by-step cooking instructions, estimated preparation/cooking time, and estimated total calories.

**AI Intelligence & Validation**
*   **Reasoning (Chain-of-Thought):** Explains its thought process, detailing exactly *why* it evaluated the ingredients a certain way and chose the specific recipe.
*   **Input Validation:** Intelligently checks if the input contains valid food items. If not, it safely rejects the input and prompts for actual ingredients.
*   **Structured Outputs:** Uses Pydantic to ensure the UI always receives perfectly formatted data from the LLM.

**Memory and User Interface**
*   **Database Integration:** Automatically saves successfully generated recipes to a Supabase database.
*   **Interactive History:** Features a sidebar that fetches and displays recent recipes. Click on any past recipe to instantly reload its full details.
*   **Robust Error Handling:** Detects and elegantly handles AI rate limits or overloaded servers with friendly error messages.

## 🛠️ Tech Stack

*   **Frontend:** [Streamlit](https://streamlit.io/)
*   **AI Model:** [Google Gemini 2.5 Flash](https://ai.google.dev/) via `google-genai`
*   **Structured Data:** Pydantic
*   **Database / Memory:** Supabase
*   **Environment Management:** `python-dotenv`

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/ai_agent.git
cd ai_agent
```

### 2. Install dependencies
Ensure you have Python installed, then run:
```bash
pip install streamlit google-genai pydantic supabase python-dotenv
```

### 3. Set up Environment Variables
Create a `.env` file in the root directory and add your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 4. Set up Supabase Database
In your Supabase project's SQL Editor, run the following query to create the necessary table:
```sql
CREATE TABLE recipes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  pantry_ingredients TEXT,
  num_people TEXT,
  is_valid_ingredients BOOLEAN,
  reasoning TEXT,
  recipe_name TEXT,
  estimated_calories INTEGER,
  estimated_servings INTEGER,
  prep_time_minutes INTEGER,
  used_ingredients JSONB,
  missing_ingredients_to_buy JSONB,
  instructions JSONB
);
```

### 5. Run the app
Start the Streamlit application:
```bash
streamlit run app.py
```

---

### Agent Design
[ USER PERCEPTION ]
  ┌──────────────────────────┐
  │ 1. Messy Ingredient Text │
  │ 2. Desired Portion Sizes │
  └─────────────┬────────────┘
                │
                ▼
     [ INTERNAL REASONING ] (Gemini 2.5 Flash Core)
  ┌──────────────────────────────────────────────────┐
  │ • Guardrail: Is this actually food?              │
  │ • Phase 1: Categorize proteins/veggies/starches  │
  │ • Phase 2: Run flavor & chemical compatibility   │
  │ • Phase 3: Evaluate critical missing elements    │
  └─────────────┬────────────────────────────────────┘
                │
                ▼
       [ AGENTIC ACTIONS ] (Internal Tools)
  ┌──────────────────────────────────────────────────┐
  │ 🛠️ Tool 1: Pydantic Strict Schema Enforcement    │
  │ 🛠️ Tool 2: Python Dietary & Calorie Calculator   │
  │ 🛠️ Tool 3: Supabase Database Sync (Memory State) │
  └─────────────┬────────────────────────────────────┘
                │
                ▼
       [ GOAL COMPLETION ]
  ┌──────────────────────────────────────────────────┐
  │  Validated, Fluff-Free JSON Recipe Dashboard     │
  └──────────────────────────────────────────────────┘


### System Architecture

[ User Input (Streamlit UI) ]
            │
            ▼
[ Input Validation Filter ] ──(Invalid)──> [ Safe Rejection & Retry Prompt ]
            │
         (Valid)
            │
            ▼
[ Gemini 2.5 Flash LLM ] 
            │
            ▼
[ Chain-of-Thought Reasoning ]
            │
            ▼
[ Pydantic Schema Tool ] 
            │
            ▼
[ Validated JSON Recipe ] ────────┐
            │                     │
            ▼                     ▼
[ Python Dietary Script ]   [ Supabase Database ]
            │                     │
            ▼                     ▼
[ Final Recipe Dashboard ] <──[ Sidebar History UI ]