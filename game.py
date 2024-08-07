import random
from enum import Enum

from network import NUM_PLAYERS, Network
from settings import CARDS_PER_HAND, NUM_LIVES

SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


class PrintColors:
    PURPLE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    ORANGE = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


# Value must be one character
class Actions(Enum):
    NEW_DEALER = 0
    INFO_NEW_DEALER = 1
    DEAL_CARDS = 2
    ASK_BET = 3
    WINNER = 4
    SHOW_BETS = 5
    ASK_CARD = 6
    RETURN_CARDS = 7
    SHOW_ROUND_RESULT = 8
    SHOW_RESULTS = 9


class Card:
    rank = 0
    suit = 0

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def to_string(self):
        return f"{RANKS[self.rank]} of {SUITS[self.suit]}"

    def encode(self):
        return f"{self.rank}-{self.suit}"


class Game:
    network: Network = {}

    # Player states
    player_id = 0
    next_player_id = 0
    dealer_id = 1
    is_alive = 1
    player_hand = []

    # Game states - Dealer
    curr_round = 1
    last_win_player_id = 0
    deck = []
    players_alive = [1] * NUM_PLAYERS  # 1 if it is alive, 0 otherwise
    players_lives = [NUM_LIVES] * NUM_PLAYERS
    players_bets = [0] * NUM_PLAYERS
    players_round_cards = [Card(0, 0)] * NUM_PLAYERS
    players_wins = [0] * NUM_PLAYERS

    def __init__(self, player_id, network):
        self.player_id = player_id
        self.next_player_id = self.next_player(player_id)
        self.network = network

        if player_id == self.dealer_id:
            self.network.has_token = 1

    ########################### UTILS ###########################

    def is_dealer(self):
        return self.dealer_id == self.player_id

    def next_player(self, current_player_id):
        return current_player_id % NUM_PLAYERS + 1

    def encode_message(self, from_player_id, to_player_id, action, data):
        return str(from_player_id) + str(to_player_id) + str(action.value) + str(data)

    def decode_message(self, message):
        from_player_id = int(message[0])
        to_player_id = int(message[1])
        action = Actions(int(message[2]))
        data = str(message[3:])

        return {
            "from_player_id": from_player_id,
            "to_player_id": to_player_id,
            "action": action,
            "data": data,
        }

    def receive_decoded_message(self):
        network_message = self.network.receive_message()
        return self.decode_message(network_message)

    def pass_message(self, decoded_message):
        encoded_message = self.encode_message(
            decoded_message["from_player_id"],
            decoded_message["to_player_id"],
            decoded_message["action"],
            decoded_message["data"],
        )
        self.network.send_message(encoded_message)

    def number_players_alive(self):
        alive = 0
        for i in self.players_alive:
            if i == 1:
                alive += 1
        return alive

    def print_purple(self, string):
        print(PrintColors.PURPLE + string + PrintColors.ENDC)

    def print_blue(self, string):
        print(PrintColors.CYAN + string + PrintColors.ENDC)

    def print_green(self, string):
        print(PrintColors.GREEN + string + PrintColors.ENDC)

    def print_red(self, string):
        print(PrintColors.RED + string + PrintColors.ENDC)

    def print_orange(self, string):
        print(PrintColors.ORANGE + string + PrintColors.ENDC)

    def print_bold(self, string):
        print(PrintColors.BOLD + string + PrintColors.ENDC)

    def print_hand(self):
        self.print_bold("=============================")
        self.print_bold("Your hand:")
        for i, card in enumerate(self.player_hand):
            self.print_bold(f"{i+1} - {card.to_string()}")
        self.print_bold("=============================")

    def print_curr_wins(self, encoded_wins):
        wins = encoded_wins.split(",")

        self.print_blue("=============================")
        self.print_blue("Number of wins:")
        for i, win in enumerate(wins):
            if self.players_alive[i]:
                self.print_blue(f"Player {i + 1} has {win} wins")
        self.print_blue("=============================")

    def print_curr_lives(self, lives):
        self.print_purple("=============================")
        self.print_purple("Lives:")
        for i, life in enumerate(lives):
            self.print_purple(f"Player {i + 1} has {life} lives")
        self.print_purple("=============================")

    def reset_states(self):
        # Reset states
        self.player_hand = []
        self.curr_round = 1
        self.last_win_player_id = 0
        self.deck = []
        self.players_bets = [0] * NUM_PLAYERS
        self.players_round_cards = [Card(0, 0)] * NUM_PLAYERS
        self.players_wins = [0] * NUM_PLAYERS

    def place_bet(self):
        bet = int(input("Place your bet - how many rounds are you going to win?\n"))
        while bet < 0 or bet > CARDS_PER_HAND:
            bet = int(input("Place your bet - how many rounds are you going to win?\n"))

        return bet

    def register_bets(self, encoded_bets):
        raw_bets = encoded_bets.split(",")

        for raw_bet in raw_bets:
            player_id, bet = str(raw_bet).split("-")
            self.players_bets[int(player_id) - 1] = int(bet)

    def select_card(self):
        self.print_hand()

        card_index = int(input("\nPlay your card: \n")) - 1

        while card_index < 0 or card_index > len(self.player_hand) - 1:
            card_index = int(input("\nPlay your card: \n")) - 1

        card = self.player_hand.pop(card_index)
        print("Card selected:", card.to_string())

        return card

    ####################### UTILS - ADMIN #######################

    def assemble_deck(self):
        for rank in range(len(RANKS)):
            for suit in range(len(SUITS)):
                self.deck.append(Card(rank, suit).encode())

    def split_cards(self):
        self.assemble_deck()
        random.shuffle(self.deck)

        hands = [
            self.deck[i * CARDS_PER_HAND : (i + 1) * CARDS_PER_HAND]
            for i in range(self.number_players_alive())
        ]

        return hands

    def finish_round(self):
        parsed_round_cards = []

        for i, card in enumerate(self.players_round_cards):
            parsed_round_cards.append(
                {
                    "player_id": i + 1,
                    "rank": card.rank,
                    "suit": card.suit,
                }
            )

        sorted_players_cards = sorted(
            parsed_round_cards, key=lambda x: (-x["rank"], -x["suit"])
        )

        win_player_id = sorted_players_cards[0]["player_id"]

        self.players_wins[win_player_id - 1] += 1
        self.last_win_player_id = win_player_id

        wins_encoded = ",".join(str(win) for win in self.players_wins)

        self.print_curr_wins(wins_encoded)

        show_round_results_message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.SHOW_ROUND_RESULT,
            wins_encoded,
        )
        self.network.send_message(show_round_results_message)

    def finish_great_round(self):
        # Decrease lives
        for i in range(NUM_PLAYERS):
            diff = abs(self.players_bets[i] - self.players_wins[i])
            self.players_lives[i] -= diff

        for i, life in enumerate(self.players_lives):
            if life <= 0:
                self.players_alive[i] = 0

        lives_encoded = ",".join([str(life) for life in self.players_lives])

        show_results_message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.SHOW_RESULTS,
            lives_encoded,
        )
        self.network.send_message(show_results_message)

    def won_game(self, winner_player):
        winner_message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.WINNER,
            str(winner_player),
        )
        self.network.send_message(winner_message)

    def verify_winners(self):
        num_alive = self.number_players_alive()

        if num_alive <= 1:
            greater_life_player = self.players_lives.index(max(self.players_lives)) + 1
            self.won_game(greater_life_player)
            return True
        elif num_alive > 1:
            return False

    def new_dealer_action(self, encoded_lives):
        to_player_id = self.next_player_id

        self.dealer_id = to_player_id

        message = self.encode_message(
            self.player_id,
            to_player_id,
            Actions.NEW_DEALER,
            encoded_lives,
        )
        self.network.send_message(message)

    ######################### ACTIONS HANDLERS #########################

    def handle_new_dealer(self):
        self.dealer_id = self.player_id

        self.reset_states()

        show_round_results_message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.INFO_NEW_DEALER,
            self.player_id,
        )
        self.network.send_message(show_round_results_message)

    def handle_info_new_dealer(self, decoded_message):
        self.dealer_id = int(decoded_message["data"])
        self.reset_states()

        decoded_message["from_player_id"] = self.player_id
        decoded_message["to_player_id"] = self.next_player_id

    def handle_deal_cards(self, decoded_message):
        cards = eval(decoded_message["data"])

        for card in cards:
            rank, suit = card.split("-")
            created_card = Card(int(rank), int(suit))
            self.player_hand.append(created_card)

        self.print_hand()

    def handle_ask_bet(self, decoded_message):
        raw_bets = decoded_message["data"].split(",")

        data_to_send = ""

        # bet protocol - PLAYER_ID-BET
        if len(raw_bets) > 0 and len(raw_bets[0]) > 0:
            print("=============================")
            print("Bets already placed:")
            for raw_bet in raw_bets:
                player_id, bet = str(raw_bet).split("-")
                print(
                    f"Player {player_id} bet: {bet}",
                )
            print("=============================")
            selected_bet = self.place_bet()
            data_to_send = (
                f"{decoded_message['data']},{str(self.player_id)}-{str(selected_bet)}"
            )
        else:
            selected_bet = self.place_bet()
            data_to_send = f"{str(self.player_id)}-{str(selected_bet)}"

        if self.is_dealer():
            self.register_bets(data_to_send)
            return

        message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.ASK_BET,
            data_to_send,
        )

        self.network.send_message(message)

    def handle_show_bets(self, decoded_message):
        bets = [int(bet) for bet in eval(decoded_message["data"])]

        print("=============================")
        print("BETS:")
        for i, bet in enumerate(bets):
            if self.players_alive[i]:
                print(
                    f"Player {i + 1} bet: {bet}",
                )
        print("=============================")

        # Pass Message to next
        decoded_message["from_player_id"] = self.player_id
        decoded_message["to_player_id"] = self.next_player_id

    def handle_ask_card(self, decoded_message):
        raw_cards = decoded_message["data"].split(",")

        data_to_send = ""

        # All Cards Played - send to dealer
        if len(raw_cards) == self.number_players_alive():
            if not self.is_dealer():
                message = self.encode_message(
                    self.player_id,
                    self.dealer_id,
                    Actions.RETURN_CARDS,
                    decoded_message["data"],
                )

                self.network.send_message(message)

                return
            else:
                self.handle_return_cards(decoded_message)
                return

        # card protocol - PLAYER_ID-RANK-SUIT
        if len(raw_cards) > 0 and len(raw_cards[0]) > 0:
            print("=============================")
            print("Cards already played:")
            for card in raw_cards:
                player_id, rank, suit = str(card).split("-")
                print(
                    f"Player {player_id} played: ",
                    Card(int(rank), int(suit)).to_string(),
                )
            print("=============================")
            selected_card = self.select_card()
            data_to_send = f"{decoded_message['data']},{str(self.player_id)}-{selected_card.encode()}"
        else:
            if len(self.player_hand) != CARDS_PER_HAND:
                self.print_green("You won last round!")
            selected_card = self.select_card()
            data_to_send = f"{str(self.player_id)}-{selected_card.encode()}"

        message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.ASK_CARD,
            data_to_send,
        )

        self.network.send_message(message)

    def ask_card_action(self, to_player_id):
        message = self.encode_message(
            self.player_id,
            to_player_id,
            Actions.ASK_CARD,
            "",
        )
        self.network.send_message(message)

    def handle_return_cards(self, decoded_message):
        raw_cards = decoded_message["data"].split(",")

        for card in raw_cards:
            player_id, rank, suit = str(card).split("-")
            played_card = Card(int(rank), int(suit))
            self.players_round_cards[int(player_id) - 1] = played_card

        self.finish_round()

    def handle_show_round_result(self, decoded_message):
        self.print_curr_wins(decoded_message["data"])

        # Pass Message to next
        decoded_message["to_player_id"] = self.next_player_id

    def handle_show_results(self, decoded_message):
        self.players_lives = [int(life) for life in decoded_message["data"].split(",")]

        for i, life in enumerate(self.players_lives):
            if life <= 0:
                self.players_alive[i] = 0

        lives = decoded_message["data"].split(",")

        self.print_curr_lives(self.players_lives)

        player_life = int(lives[self.player_id - 1])
        if player_life <= 0:
            self.print_red("You died :(\n")
            self.is_alive = 0

        # Pass Message to next
        decoded_message["from_player_id"] = self.player_id
        decoded_message["to_player_id"] = self.next_player_id

    def handle_winner(self, decoded_message):
        winner = int(decoded_message["data"])

        if winner == self.player_id:
            self.print_green("You won! :)")
        else:
            self.print_red(f"Player {winner} won!")

        # Pass Message to next
        decoded_message["from_player_id"] = self.player_id
        decoded_message["to_player_id"] = self.next_player_id
        self.pass_message(decoded_message)

    ####################### START GAME #######################

    def start(self):
        net = self.network
        while True:
            if self.is_dealer():
                self.print_orange("===========YOU ARE THE DEALER===========")
                hands = self.split_cards()

                # Deal Cards
                last_to_player_id = self.player_id
                for hand in hands:
                    to_player_id = self.next_player(last_to_player_id)
                    # To player is not alive
                    while not self.players_alive[to_player_id - 1]:
                        to_player_id = self.next_player(to_player_id)

                    last_to_player_id = to_player_id

                    message = self.encode_message(
                        self.player_id,
                        to_player_id,
                        Actions.DEAL_CARDS,
                        hand,
                    )
                    net.send_message(message)
                    message = self.receive_decoded_message()
                    if (
                        message["to_player_id"] == self.player_id
                        and message["action"] == Actions.DEAL_CARDS
                    ):
                        self.handle_deal_cards(message)

                # Ask bets
                message = self.encode_message(
                    self.player_id,
                    self.next_player_id,
                    Actions.ASK_BET,
                    "",
                )
                self.network.send_message(message)
                decoded_message = self.receive_decoded_message()

                if decoded_message["action"] == Actions.ASK_BET:
                    self.handle_ask_bet(decoded_message)
                else:
                    print("Game flow was broken")
                    exit(1)

                # Show bets
                message = self.encode_message(
                    self.player_id,
                    self.next_player_id,
                    Actions.SHOW_BETS,
                    self.players_bets,
                )
                self.network.send_message(message)

                decoded_message = self.receive_decoded_message()

                if decoded_message["action"] == Actions.SHOW_BETS:
                    self.handle_show_bets(decoded_message)
                else:
                    print("Game flow was broken")
                    exit(1)

                self.ask_card_action(self.next_player_id)

            # Round loop
            while True:
                decoded_message = self.receive_decoded_message()
                action = decoded_message["action"]

                if (
                    decoded_message["to_player_id"] == self.player_id and self.is_alive
                ) or action == Actions.WINNER:
                    # print(
                    #     f"Player on port {self.network.player_port} received: {decoded_message}"
                    # )

                    match action:
                        case Actions.NEW_DEALER:
                            self.handle_new_dealer()
                            continue
                        case Actions.INFO_NEW_DEALER:
                            if not self.is_dealer():
                                self.handle_info_new_dealer(decoded_message)
                            else:
                                # Start another game
                                break
                        case Actions.DEAL_CARDS:
                            self.handle_deal_cards(decoded_message)

                        case Actions.ASK_BET:
                            self.handle_ask_bet(decoded_message)
                            continue

                        case Actions.SHOW_BETS:
                            if not self.is_dealer():
                                self.handle_show_bets(decoded_message)
                            else:
                                continue

                        case Actions.ASK_CARD:
                            self.handle_ask_card(decoded_message)
                            continue

                        case Actions.RETURN_CARDS:
                            if self.is_dealer():
                                self.handle_return_cards(decoded_message)
                                continue

                        case Actions.SHOW_ROUND_RESULT:
                            if not self.is_dealer():
                                self.handle_show_round_result(decoded_message)
                            else:
                                if self.curr_round == CARDS_PER_HAND:
                                    self.finish_great_round()
                                else:
                                    # New round
                                    self.ask_card_action(self.last_win_player_id)
                                    self.curr_round += 1
                                continue

                        case Actions.SHOW_RESULTS:
                            self.handle_show_results(decoded_message)
                            if self.is_dealer():
                                if self.verify_winners():
                                    continue

                                self.new_dealer_action(decoded_message["data"])
                                continue
                        case Actions.WINNER:
                            self.handle_winner(decoded_message)
                            exit(0)

                        case _:
                            print("Message with unknown action")
                            exit(1)
                elif (
                    not self.is_alive
                    and decoded_message["to_player_id"] == self.player_id
                ):
                    decoded_message["to_player_id"] = self.next_player_id
                self.pass_message(decoded_message)
