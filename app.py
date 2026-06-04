import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the function in agent.py
from agent import generate_meal_plan 
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# Set up the UI layout
st.set_page_config(page_title="Sangkap AI", page_icon="🍳")

# Initialize session state for selected recipe
if "selected_recipe" not in st.session_state:
    st.session_state.selected_recipe = None

# Sidebar: Recipe History
with st.sidebar:
    st.header("📜 Recipe History")
    if supabase:
        try:
            # Fetch the latest 20 successful recipes from Supabase
            response = supabase.table("recipes").select("*").eq("is_valid_ingredients", True).order("created_at", desc=True).limit(20).execute()
            recipes_data = response.data
            
            if recipes_data:
                # Display the recipes as buttons in the sidebar
                for i, r_data in enumerate(recipes_data):
                    if st.button(r_data.get("recipe_name", "Recipe"), key=f"hist_{r_data.get('id', i)}", use_container_width=True):
                        st.session_state.selected_recipe = r_data
            else:
                st.info("No past recipes yet. Generate your first one!")
        except Exception as e:
            st.error(f"Could not load history: {e}")
    else:
        st.info("Set up Supabase to remember past recipes!")

st.title("🍳 Sangkap AI")
st.write("Tell me what ingredients you have, and I'll generate a structured recipe for you.")

# Create a container for the results to place them above the input
results_container = st.container()

# User input box
user_ingredients = st.text_input("What's in your pantry?", placeholder="e.g., Eggs, rice, soy sauce, old spinach")

# Option for number of people
num_people = st.selectbox("How many people are you cooking for?", ["1 person", "2 people", "3 people", "Many people (4+)"])

# Trigger the agent
if st.button("Generate Meal"):
    if user_ingredients:
        with results_container:
            with st.spinner("The AI is analyzing your ingredients..."):
                try:
                    # Call the agent
                    recipe = generate_meal_plan(user_ingredients, num_people)
                    
                    if recipe.is_valid_ingredients:
                        db_record = recipe.model_dump()
                        db_record["pantry_ingredients"] = user_ingredients
                        db_record["num_people"] = num_people
                        
                        # Save to Supabase memory
                        if supabase:
                            try:
                                supabase.table("recipes").insert(db_record).execute()
                            except Exception as db_error:
                                st.error(f"Failed to save recipe to database: {db_error}")
                                
                        # Update session state with the new recipe
                        st.session_state.selected_recipe = db_record
                    else:
                        st.warning(recipe.recipe_name)
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "UNAVAILABLE" in error_msg:
                        st.warning("The AI servers are currently experiencing high demand. Please wait a few seconds and try again!")
                    elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        st.warning("You've hit the AI's rate limit! Please wait a little while before asking for another recipe.")
                    else:
                        st.warning("Oops! I couldn't generate a recipe from that. Please try entering actual food items.")
                        st.error(f"Developer Details: {e}")
    else:
        st.warning("Please enter some ingredients first!")

# Display the selected recipe (either newly generated or from history)
if st.session_state.selected_recipe:
    with results_container:
        r = st.session_state.selected_recipe
        
        st.success(f"**{r.get('recipe_name')}**")
        
        with st.expander("🧠 Sangkap AI's Reasoning"):
            st.write(r.get("reasoning"))

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"⏱️ **Prep Time:** {r.get('prep_time_minutes', 0)} mins")
            st.write(f"🔥 **Estimated Calories:** {r.get('estimated_calories', 0)} kcal")
            st.write(f"🍽️ **Estimated Servings:** {r.get('estimated_servings', 0)}")
            st.write("✅ **Using what you have:**")
            for item in r.get('used_ingredients', []):
                st.write(f"- {item}")
        
        with col2:
            st.write("🛒 **Quick Shopping List:**")
            for item in r.get('missing_ingredients_to_buy', []):
                st.write(f"- {item}")
                
            st.write("---")
            st.write("📝 **Instructions:**")
            for i, step in enumerate(r.get('instructions', []), 1):
                st.write(f"**Step {i}:** {step}")

st.markdown("---")
st.caption("⚠️ **Disclaimer:** These recipes are generated by Artificial Intelligence. Please use your best judgment regarding food safety, cooking temperatures, and dietary restrictions or allergies. AI can make mistakes!")