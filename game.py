import random
from enum import Enum

from network import NUM_PLAYERS, Network
from settings import CARDS_PER_HAND

SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


# Its value must be one character
class Actions(Enum):
    NEW_DEALER = 0
    INFO_NEW_DEALER = 1
    DEAL_CARDS = 2
    ASK_BET = 3
    PLACE_BET = 4
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

    # Players states
    player_id = 0
    next_player_id = 0
    dealer_id = 1
    player_hand = []

    # Game states
    curr_round = 1
    last_win_player_id = 0
    deck = []
    players_points = [0] * NUM_PLAYERS
    players_bets = [0] * NUM_PLAYERS
    players_round_cards = [Card(0, 0)] * NUM_PLAYERS
    players_wins = [0] * NUM_PLAYERS

    def __init__(self, player_id, network):
        self.player_id = player_id
        self.next_player_id = self.next_player(player_id)
        self.network = network

        if player_id == self.dealer_id:
            self.network.has_token = 1

    def assemble_deck(self):
        for rank in range(len(RANKS)):
            for suit in range(len(SUITS)):
                self.deck.append(Card(rank, suit).encode())

    def is_dealer(self):
        return self.dealer_id == self.player_id

    def next_player(self, current_player_id):
        return current_player_id % NUM_PLAYERS + 1

    def encode_message(self, from_player_id, to_player_id, action, data):
        return str(from_player_id) + str(to_player_id) + str(action.value) + str(data)

    def receive_decoded_message(self):
        network_message = self.network.receive_message()
        return self.decode_message(network_message)

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

    def pass_message(self, decoded_message):
        encoded_message = self.encode_message(
            decoded_message["from_player_id"],
            decoded_message["to_player_id"],
            decoded_message["action"],
            decoded_message["data"],
        )
        self.network.send_message(encoded_message)

    def split_cards(self):
        self.assemble_deck()
        random.shuffle(self.deck)

        hands = [
            self.deck[i * CARDS_PER_HAND : (i + 1) * CARDS_PER_HAND]
            for i in range(NUM_PLAYERS)
        ]

        return hands

    def finish_round(self):
        # Parse dict
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

    def print_hand(self):
        print("=============================")
        print("Your hand:")
        for i, card in enumerate(self.player_hand):
            print(f"{i+1} - {card.to_string()}")
        print("=============================")

    def reset_states(self):
        # Reset states
        self.player_hand = []
        self.curr_round = 1
        self.last_win_player_id = 0
        self.deck = []
        self.players_bets = [0] * NUM_PLAYERS
        self.players_round_cards = [Card(0, 0)] * NUM_PLAYERS
        self.players_wins = [0] * NUM_PLAYERS

    def handle_new_dealer(self, decoded_message):
        self.players_points = [
            int(point) for point in decoded_message["data"].split(",")
        ]

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

        # ======================================

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
            selected_card = self.select_card()
            data_to_send = f"{str(self.player_id)}-{selected_card.encode()}"

        # if self.is_dealer():
        #     self.players_round_cards[self.player_id - 1] = selected_card

        message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.ASK_CARD,
            data_to_send,
        )

        self.network.send_message(message)

        # ======================================

        bet = int(input("Place your bet - how many rounds are you going to win?\n"))
        while bet < 0 or bet > CARDS_PER_HAND:
            bet = int(input("Place your bet - how many rounds are you going to win?\n"))
        message = self.encode_message(
            self.player_id,
            self.dealer_id,
            Actions.PLACE_BET,
            bet,
        )
        self.network.send_message(message)

    def handle_show_bet(self, decoded_message):
        print("=============================")
        print("BETS:")
        print(decoded_message["data"])
        print("=============================")

        # Pass Message to next
        decoded_message["from_player_id"] = self.player_id
        decoded_message["to_player_id"] = self.next_player_id

    def select_card(self):
        self.print_hand()

        card_index = int(input("\nPlay your card: \n")) - 1

        while card_index < 0 or card_index > len(self.player_hand) - 1:
            card_index = int(input("\nPlay your card: \n")) - 1

        card = self.player_hand.pop(card_index)
        print("Card selected:", card.to_string())

        return card

    def handle_ask_card(self, decoded_message):
        raw_cards = decoded_message["data"].split(",")

        data_to_send = ""

        # All Cards Played - send to dealer
        if len(raw_cards) == NUM_PLAYERS:
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
            selected_card = self.select_card()
            data_to_send = f"{str(self.player_id)}-{selected_card.encode()}"

        # if self.is_dealer():
        #     self.players_round_cards[self.player_id - 1] = selected_card

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

    def new_dealer_action(self, encoded_points):
        to_player_id = self.next_player_id

        self.dealer_id = to_player_id

        message = self.encode_message(
            self.player_id,
            to_player_id,
            Actions.NEW_DEALER,
            encoded_points,
        )
        self.network.send_message(message)

    # Only the dealer will do this action
    def handle_return_cards(self, decoded_message):
        raw_cards = decoded_message["data"].split(",")

        for card in raw_cards:
            player_id, rank, suit = str(card).split("-")
            played_card = Card(int(rank), int(suit))
            self.players_round_cards[int(player_id) - 1] = played_card

        self.finish_round()

    def print_curr_wins(self, encoded_wins):
        wins = encoded_wins.split(",")

        print("=============================")
        print("Number of wins:")
        for i, win in enumerate(wins):
            print(f"Player {i + 1} has {win} wins")
        print("=============================")

    def print_curr_points(self, encoded_points):
        points = encoded_points.split(",")

        print("=============================")
        print("Points:")
        for i, point in enumerate(points):
            print(f"Player {i + 1} has {point} points")
        print("=============================")

    def handle_show_round_result(self, decoded_message):
        self.print_curr_wins(decoded_message["data"])

        # Pass Message to next
        decoded_message["to_player_id"] = self.next_player_id

    def finish_great_round(self):
        # Decrease lives
        smallest_diff = 10000
        smallest_diff_player_ids = []
        for i in range(NUM_PLAYERS):
            diff = abs(self.players_bets[i] - self.players_wins[i])
            if diff < smallest_diff:
                smallest_diff_player_ids = []
                smallest_diff_player_ids.append(i + 1)
                smallest_diff = diff
            elif diff == smallest_diff:
                smallest_diff_player_ids.append(i + 1)

        for player_id in smallest_diff_player_ids:
            self.players_points[player_id - 1] += 1

        points_encoded = ",".join([str(point) for point in self.players_points])

        self.print_curr_points(points_encoded)

        show_results_message = self.encode_message(
            self.player_id,
            self.next_player_id,
            Actions.SHOW_RESULTS,
            points_encoded,
        )
        self.network.send_message(show_results_message)

    def handle_show_results(self, decoded_message):
        self.print_curr_points(decoded_message["data"])

        # Pass Message to next
        decoded_message["from_player_id"] = self.player_id
        decoded_message["to_player_id"] = self.next_player_id

    def start(self):
        net = self.network
        while True:
            if self.is_dealer():
                print("===========YOU ARE THE DEALER===========")
                hands = self.split_cards()

                for i, hand in enumerate(hands):
                    message = self.encode_message(
                        self.player_id,
                        self.next_player(self.player_id + i),
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
                    self.next_player,
                    Actions.ASK_BET,
                    "",
                )
                self.network.send_message(message)
                decoded_message = self.receive_decoded_message()

                self.handle_ask_bet(decoded_message)

                # if message["action"] == Actions.PLACE_BET:
                #     self.players_bets[int(message["from_player_id"]) - 1] = int(
                #         message["data"]
                #     )

                # # Place dealer's bet
                # if (
                #     message["to_player_id"] == self.player_id
                #     and message["action"] == Actions.ASK_BET
                # ):
                #     bet = int(
                #         input(
                #             "Insira a sua aposta - Quantas rodadas você vai ganhar?\n"
                #         )
                #     )
                #     while bet < 0 or bet > NUM_PLAYERS:
                #         bet = int(
                #             input(
                #                 "Insira a sua aposta - Quantas rodadas você vai ganhar?\n"
                #             )
                #         )
                #     self.players_bets[int(self.player_id) - 1] = bet

                # Show bets
                message = self.encode_message(
                    self.player_id,
                    self.next_player_id,
                    Actions.SHOW_BETS,
                    self.players_bets,
                )
                self.network.send_message(message)

                decoded_message = self.receive_decoded_message()

                self.handle_show_bet(decoded_message)

                self.ask_card_action(self.next_player_id)

            # Round loop
            while True:
                decoded_message = self.receive_decoded_message()
                action = decoded_message["action"]

                if decoded_message["to_player_id"] == self.player_id:
                    # print(
                    #     f"Player on port {self.network.player_port} received: {decoded_message}"
                    # )

                    match action:
                        case Actions.NEW_DEALER:
                            self.handle_new_dealer(decoded_message)
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
                            self.handle_ask_bet()
                            continue

                        case Actions.SHOW_BETS:
                            if not self.is_dealer():
                                self.handle_show_bet(decoded_message)
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
                            print(f"======== Round {self.curr_round} ========")
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
                            if not self.is_dealer():
                                self.handle_show_results(decoded_message)
                            else:
                                self.new_dealer_action(decoded_message["data"])
                                continue
                        case _:
                            print("Message with unknown action")
                            exit(1)
                self.pass_message(decoded_message)
