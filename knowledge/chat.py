import os
import sys
from query import hybrid_query
from dotenv import load_dotenv

# Load configurations
load_dotenv()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_welcome():
    print("=" * 60)
    print("   بەخێربێن بۆ یاریدەدەری پزیشکی کوردی (Kurdish Medical AI)   ")
    print("=" * 60)
    print("تۆ دەتوانی هەر پرسیارێکی پزیشکی بکەیت بە زمانی کوردی.")
    print("بۆ چوونەدەرەوە بنووسە 'exit' یان 'quit'.")
    print("-" * 60)

import time
import threading

def loading_animation(stop_event):
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r🔍 خەریکی گەڕانم... {chars[i % len(chars)]} ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + " " * 30 + "\r")

def main():
    clear_screen()
    print_welcome()
    
    while True:
        try:
            # Get user input
            question = input("\n👤 پرسیارەکەت بنووسە: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['exit', 'quit', 'exit()', 'بڕۆ دەرەوە']:
                print("\n👋 ماڵئاوا! هیوای تەندروستییەکی باشت بۆ دەخوازم.")
                break
            
            # Start loading animation
            stop_event = threading.Event()
            loader = threading.Thread(target=loading_animation, args=(stop_event,))
            loader.start()
            
            try:
                # Call the hybrid query function
                response = hybrid_query(question)
            finally:
                stop_event.set()
                loader.join()
            
            print("\n" + "✨" + "─" * 28 + " وەڵام " + "─" * 28 + "✨")
            print(response)
            print("─" * 67)
            
        except KeyboardInterrupt:
            print("\n\nماڵئاوا!")
            break
        except Exception as e:
            print(f"\nهەڵەیەک ڕوویدا: {e}")

if __name__ == "__main__":
    main()
