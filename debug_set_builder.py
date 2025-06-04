#!/usr/bin/env python3
"""
Debug wrapper for Pokemon Set Builder
This script runs the Pokemon Set Builder with extra error handling
to help troubleshoot crashes.
"""

import sys
import traceback
import os

def main():
    try:
        print("=== Starting Pokemon Set Builder in Debug Mode ===")
        print("This will catch and display any errors that occur")
        
        # Add the current directory to sys.path if not already there
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        # Import the Pokemon Set Builder
        from pokemon_set_builder import PokemonSetBuilder
        from PyQt5.QtWidgets import QApplication
        
        # Create the application
        app = QApplication(sys.argv)
        
        # Create and show the main window
        window = PokemonSetBuilder()
        window.show()
        
        # Start the event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print("\n=== ERROR OCCURRED ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        print("\n=== END OF ERROR ===")
        
        # Keep the console window open
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
