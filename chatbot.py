# chatbot.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from tools import build_tools_for_token

load_dotenv()

class WellUChatbot:
    def __init__(self, token: str):
        self.token = token
        self.conversation_history = []

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7
        )

        # Build tools specifically for this user's token
        # The token is baked into each tool function, so 
        # the AI never sees or handles it directly
        self.tools = build_tools_for_token(token)

        self.user_context = self._build_user_context()
        self.agent = self._build_agent()

    def _build_user_context(self):
        from fake_backend import (
            get_user_profile,
            get_workout_plan,
            get_nutrition_plan,
            get_progress
        )

        profile = get_user_profile(self.token)
        workout = get_workout_plan(self.token)
        nutrition = get_nutrition_plan(self.token)
        progress = get_progress(self.token)

        context = f"""
        You are WellU, a personal AI wellness coach.

        --- USER PROFILE ---
        {profile}

        --- CURRENT WORKOUT PLAN ---
        {workout}

        --- CURRENT NUTRITION PLAN ---
        {nutrition}

        --- CURRENT PROGRESS ---
        {progress}

        --- PERSONALITY & BEHAVIOR RULES ---
        - You are friendly, motivating, and supportive
        - You always personalize responses using the user's data above
        - When user mentions eating something, use the log_meal tool
        - When user mentions a strength exercise (bench press, squats, 
          deadlifts, etc), use log_strength_exercise
        - When user mentions a cardio exercise (running, cycling, 
          swimming, etc), use log_cardio_exercise
        - When user asks about current stats, use fetch_progress
        - Keep responses concise and clear, not too long
        - If user asks something unrelated to wellness, politely 
          bring them back on topic

        --- EXERCISE CHANGE RULES ---
        - If the user dislikes or wants to change an exercise but 
          does NOT explain why, ask them why before suggesting alternatives
        - Only after understanding the reason, suggest alternatives
        - Never suggest an exercise that could worsen a known injury 
          if injury data is available in the profile above
        - Only call modify_workout_exercise after explicit confirmation

        --- NUTRITION CHANGE RULES ---
        - If the user dislikes or wants to change a food but does NOT 
          explain why, ask them why before suggesting alternatives
        - Never suggest food containing allergens if allergy data is 
          available in the profile above
        - Only call modify_meal_item after explicit confirmation
        """
        return context

    def _build_agent(self):
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.user_context
        )
        return agent

    def chat(self, user_message: str):
        self.conversation_history.append(HumanMessage(content=user_message))

        result = self.agent.invoke({
            "messages": self.conversation_history
        })

        response_text = result["messages"][-1].content

        self.conversation_history.append(AIMessage(content=response_text))

        return response_text