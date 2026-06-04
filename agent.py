import os
from pydantic import BaseModel, Field
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# JSON structure to validate if input contains food
class RecipeRecommendation(BaseModel):
    is_valid_ingredients: bool = Field(description="True if the user provided actual food ingredients, False otherwise")
    reasoning: str = Field(description="Step-by-step reasoning or Chain-of-Thought explaining how you evaluated the ingredients to choose this recipe.")
    recipe_name: str = Field(description="A creative and appetizing name for the recipe. If no food provided, return a friendly error message here.")
    estimated_calories: int = Field(description="Estimated total calories for the entire recipe. Set to 0 if no food provided.")
    estimated_servings: int = Field(description="Estimated number of servings this recipe will make. Set to 0 if no food provided.")
    prep_time_minutes: int = Field(description="Estimated preparation and cooking time in minutes. Set to 0 if no food provided.")
    used_ingredients: list[str] = Field(description="Ingredients from the user's pantry that will be used, including estimated measurements (e.g., '1 cup white rice')")
    missing_ingredients_to_buy: list[str] = Field(description="1 to 3 critical ingredients to buy to complete the meal, including measurements (e.g., '2 tbsp soy sauce')")
    instructions: list[str] = Field(description="Step-by-step cooking instructions")

# Initialize the Gemini client
client = genai.Client()

def generate_meal_plan(pantry_ingredients: str, num_people: str) -> RecipeRecommendation:
    """Agent function that takes raw ingredients and outputs a structured recipe."""
    
    system_prompt = """
    You are an expert culinary AI agent. 
    Your goal is to evaluate the user's available pantry ingredients and suggest a practical, delicious recipe.
    Before suggesting the recipe, provide step-by-step reasoning for your choices.
    Also, estimate the total calories for the final meal.
    If the user's input does not contain any valid food ingredients, set `is_valid_ingredients` to false, provide a gentle error message in `recipe_name` asking for food, and leave the other fields empty or 0.
    Prioritize using what the user already has, but suggest a few essential missing ingredients if it significantly improves the dish.
    Make sure to include specific measurements for both used and missing ingredients.
    You must strictly adhere to the provided output format.
    """
    
    # Call Gemini using structured outputs
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            system_prompt,
            f"Here is what I have in my pantry: {pantry_ingredients}. I want to cook a meal for {num_people}."
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": RecipeRecommendation,
            "temperature": 0.4,
        }
    )
    
    # Return the validated Python object
    return response.parsed

# Execution
if __name__ == "__main__":
    my_pantry = "Chicken breast, soy sauce, garlic, old carrots, white rice"
    print(f"Analyzing pantry: {my_pantry}...\n")
    
    recipe = generate_meal_plan(my_pantry, "2 people")
    
    if recipe.is_valid_ingredients:
        print(f"🍽️ Recipe: {recipe.recipe_name}")
        print(f"🧠 Reasoning: {recipe.reasoning}")
        print(f"🔥 Calories: {recipe.estimated_calories} kcal")
        print(f"👥 Servings: {recipe.estimated_servings}")
        print(f"⏱️ Time: {recipe.prep_time_minutes} mins")
        print(f"✅ Using: {', '.join(recipe.used_ingredients)}")
        print(f"🛒 Shopping List: {', '.join(recipe.missing_ingredients_to_buy)}")
    else:
        print(f"⚠️ Error: {recipe.recipe_name}")