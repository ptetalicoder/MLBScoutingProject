"""
CRUD operations for the Player table.
Provides functions to Create, Read, Update, and Delete player records.
"""

import sqlite3
import streamlit as st
from typing import Optional, Dict, Any, List, Tuple

from db import dict_row_factory


class PlayerCRUD:
    """Handles all CRUD operations for the Player table."""

    def __init__(self, conn):
        """Initialize with a database connection."""
        self.conn = conn

    def create_player(self, first_name: str, last_name: str, date_of_birth: Optional[str],
                      position: Optional[str], height: Optional[int], weight: Optional[int],
                      throws: Optional[str], bats: Optional[str], player_level: Optional[str]) -> int:
        """
        Create a new player record.

        Args:
            first_name: Player's first name
            last_name: Player's last name
            date_of_birth: Player's date of birth (YYYY-MM-DD format)
            position: Player's position (e.g., 'SS', 'C', 'P')
            height: Player's height in inches
            weight: Player's weight in pounds
            throws: Hand throwing preference ('L' or 'R')
            bats: Hand batting preference ('L', 'R', or 'S')
            player_level: League level ('MLB', 'MiLB', 'College', etc.)

        Returns:
            The PlayerID of the newly created player

        Raises:
            Exception: If database insertion fails
        """
        try:
            cursor = self.conn.cursor()

            query = """
            INSERT INTO Player
            (FirstName, LastName, DateOfBirth, Position, Height, Weight, Throws, Bats, PlayerLevel)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            values = (first_name, last_name, date_of_birth, position, height, weight, throws, bats, player_level)

            cursor.execute(query, values)
            self.conn.commit()

            player_id = cursor.lastrowid
            cursor.close()

            return player_id

        except sqlite3.Error as e:
            st.error(f"Database error creating player: {e}")
            raise
        except Exception as e:
            st.error(f"Error creating player: {e}")
            raise

    def read_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single player by PlayerID.

        Args:
            player_id: The PlayerID to retrieve

        Returns:
            A dictionary with player information, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.row_factory = dict_row_factory

            query = "SELECT * FROM Player WHERE PlayerID = ?"
            cursor.execute(query, (player_id,))

            result = cursor.fetchone()
            cursor.close()

            return result

        except sqlite3.Error as e:
            st.error(f"Database error reading player: {e}")
            return None
        except Exception as e:
            st.error(f"Error reading player: {e}")
            return None

    def read_all_players(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve all players with pagination.

        Args:
            limit: Maximum number of records to return (default 100)
            offset: Number of records to skip (default 0)

        Returns:
            A list of dictionaries with player information
        """
        try:
            cursor = self.conn.cursor()
            cursor.row_factory = dict_row_factory

            query = "SELECT * FROM Player ORDER BY LastName, FirstName LIMIT ? OFFSET ?"
            cursor.execute(query, (limit, offset))

            results = cursor.fetchall()
            cursor.close()

            return results

        except sqlite3.Error as e:
            st.error(f"Database error reading players: {e}")
            return []
        except Exception as e:
            st.error(f"Error reading players: {e}")
            return []

    def search_players(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for players by name (FirstName or LastName or full name) or PlayerID.

        Args:
            search_term: The name, partial name, or PlayerID to search for

        Returns:
            A list of dictionaries with matching player information
        """
        try:
            cursor = self.conn.cursor()
            cursor.row_factory = dict_row_factory

            # Check if search term is a number (PlayerID)
            try:
                player_id = int(search_term)
                query_id = "SELECT * FROM Player WHERE PlayerID = ?"
                cursor.execute(query_id, (player_id,))
                results = cursor.fetchall()

                if results:
                    cursor.close()
                    return results
            except (ValueError, TypeError):
                # Not a number, continue with name search
                pass

            # Support searching by:
            # 1. FirstName or LastName individually
            # 2. Full name (FirstName LastName)
            # 3. Partial matches
            search_pattern = f"%{search_term}%"

            # Try exact full name match first
            query_full_name = """
            SELECT * FROM Player
            WHERE (FirstName || ' ' || LastName) LIKE ?
            ORDER BY LastName, FirstName
            """
            cursor.execute(query_full_name, (search_pattern,))
            results = cursor.fetchall()

            # If no results from full name, try individual first/last names
            if not results:
                query_individual = """
                SELECT * FROM Player
                WHERE FirstName LIKE ? OR LastName LIKE ?
                ORDER BY LastName, FirstName
                """
                cursor.execute(query_individual, (search_pattern, search_pattern))
                results = cursor.fetchall()

            cursor.close()
            return results

        except sqlite3.Error as e:
            st.error(f"Database error searching players: {e}")
            return []
        except Exception as e:
            st.error(f"Error searching players: {e}")
            return []

    def update_player(self, player_id: int, **kwargs) -> bool:
        """
        Update a player's information.

        Args:
            player_id: The PlayerID to update
            **kwargs: Field names and values to update (e.g., first_name='John', position='SS')
                     Accepted fields: first_name, last_name, date_of_birth, position,
                                      height, weight, throws, bats, player_level

        Returns:
            True if update was successful, False otherwise
        """
        # Map parameter names to database column names
        field_mapping = {
            'first_name': 'FirstName',
            'last_name': 'LastName',
            'date_of_birth': 'DateOfBirth',
            'position': 'Position',
            'height': 'Height',
            'weight': 'Weight',
            'throws': 'Throws',
            'bats': 'Bats',
            'player_level': 'PlayerLevel'
        }

        if not kwargs:
            st.warning("No fields to update")
            return False

        try:
            cursor = self.conn.cursor()

            # Build the SET clause dynamically
            set_clauses = []
            values = []

            for key, value in kwargs.items():
                if key in field_mapping:
                    set_clauses.append(f"{field_mapping[key]} = ?")
                    values.append(value)
                else:
                    st.warning(f"Unknown field: {key}")

            if not set_clauses:
                st.error("No valid fields to update")
                return False

            # Add player_id to the end of values for the WHERE clause
            values.append(player_id)

            set_sql = ", ".join(set_clauses)
            query = f"UPDATE Player SET {set_sql} WHERE PlayerID = ?"

            cursor.execute(query, values)
            self.conn.commit()

            if cursor.rowcount > 0:
                return True
            else:
                st.warning(f"No player found with ID {player_id}")
                return False

        except sqlite3.Error as e:
            st.error(f"Database error updating player: {e}")
            return False
        except Exception as e:
            st.error(f"Error updating player: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def delete_player(self, player_id: int) -> bool:
        """
        Delete a player record.

        Args:
            player_id: The PlayerID to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check if player exists first
            cursor.execute("SELECT PlayerID FROM Player WHERE PlayerID = ?", (player_id,))
            if not cursor.fetchone():
                st.error(f"No player found with ID {player_id}")
                return False

            # Delete the player
            query = "DELETE FROM Player WHERE PlayerID = ?"
            cursor.execute(query, (player_id,))
            self.conn.commit()

            return True

        except sqlite3.Error as e:
            st.error(f"Database error deleting player: {e}")
            return False
        except Exception as e:
            st.error(f"Error deleting player: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def get_player_count(self) -> int:
        """
        Get the total number of players in the database.

        Returns:
            The total count of players
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM Player")
            count = cursor.fetchone()[0]
            cursor.close()

            return count

        except Exception as e:
            st.error(f"Error counting players: {e}")
            return 0
