"""
Print Eviolite Users Step

This module provides a pipeline step to print all Pokemon that are better with Eviolite than evolved.
It displays their name, original BST, and "eviolite BST" for analysis.
"""

from framework import Step
from steps import EvioliteUser

class PrintEvioliteUsersStep(Step):
    """Pipeline step to print all EvioliteUsers with their stats.
    
    This step retrieves the EvioliteUser extractor and prints a formatted list
    of all Pokemon that benefit more from Eviolite than evolution, showing their
    name, original BST, and Eviolite-boosted BST.
    
    For beginners:
    - This step doesn't modify any data, it just displays information
    - "BST" stands for "Base Stat Total" (the sum of all six stats)
    - "Eviolite BST" is the adjusted BST with Defense and Sp. Defense boosted by 50%
    """
    
    def __init__(self, show_candidates=False):
        """Initialize the PrintEvioliteUsersStep.
        
        Args:
            show_candidates (bool): If True, also prints non-Eviolite users that can evolve
        """
        self.show_candidates = show_candidates
    
    def run(self, context):
        """Run the step to print all Eviolite Users.
        
        Args:
            context (RandomizationContext): Randomization context
        """
        # Get the EvioliteUser extractor
        eviolite_users = context.get(EvioliteUser)
        
        # Print header
        print("\n===== EVIOLITE USERS REPORT =====")
        print(f"Found {len(eviolite_users.eviolite_users)} Eviolite Users out of {len(eviolite_users.candidates)} candidates")
        
        # Print detailed header for Eviolite Users
        print("\n{:<20} {:<6} {:<6} {:<6} {:<6} {:<6} {:<6} {:<10} {:<15} {:<10}".format(
            "Pokemon Name", "HP", "Atk", "Def", "SpA", "SpD", "Spd", "Original BST", "Eviolite BST", "Difference"
        ))
        print("-" * 90)
        
        # Print each Eviolite User sorted by name
        for pokemon in sorted(eviolite_users.eviolite_users, key=lambda p: p.name):
            # Get analysis data
            analysis = pokemon._eviolite_analysis
            original_bst = analysis['original_bst']
            eviolite_bst = analysis['eviolite_bst']
            difference = eviolite_bst - original_bst
            
            # Get individual stats
            hp = pokemon.hp
            attack = pokemon.attack
            defense = pokemon.defense
            sp_attack = pokemon.sp_attack
            sp_defense = pokemon.sp_defense
            speed = pokemon.speed
            
            # Print formatted row with all stats
            print("{:<20} {:<6} {:<6} {:<6} {:<6} {:<6} {:<6} {:<10} {:<15} {:<+10}".format(
                pokemon.name, hp, attack, defense, sp_attack, sp_defense, speed, 
                original_bst, eviolite_bst, difference
            ))
        
        # Optionally show all evolution candidates that aren't Eviolite Users
        if self.show_candidates:
            non_eviolite_users = [p for p in eviolite_users.candidates 
                               if p not in eviolite_users.eviolite_users]
            
            if non_eviolite_users:
                print("\n===== OTHER EVOLUTION CANDIDATES =====")
                print("{:<20} {:<6} {:<6} {:<6} {:<6} {:<6} {:<6} {:<10} {:<15} {:<10}".format(
                    "Pokemon Name", "HP", "Atk", "Def", "SpA", "SpD", "Spd", "Original BST", "Eviolite BST", "Difference"
                ))
                print("-" * 90)
                
                for pokemon in sorted(non_eviolite_users, key=lambda p: p.name):
                    analysis = pokemon._eviolite_analysis
                    original_bst = analysis['original_bst']
                    eviolite_bst = analysis['eviolite_bst']
                    difference = eviolite_bst - original_bst
                    
                    # Get individual stats
                    hp = pokemon.hp
                    attack = pokemon.attack
                    defense = pokemon.defense
                    sp_attack = pokemon.sp_attack
                    sp_defense = pokemon.sp_defense
                    speed = pokemon.speed
                    
                    print("{:<20} {:<6} {:<6} {:<6} {:<6} {:<6} {:<6} {:<10} {:<15} {:<+10}".format(
                        pokemon.name, hp, attack, defense, sp_attack, sp_defense, speed, 
                        original_bst, eviolite_bst, difference
                    ))
        
        print("\n===== END OF REPORT =====")
