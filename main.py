import sys
import argparse

from game import Game
from network import Network


def main():
    parser = argparse.ArgumentParser(description="Game client")
    parser.add_argument(
        "-n", "--player-id", type=int, required=True, help="ID of this player"
    )
    parser.add_argument(
        "-i", "--player-ip", type=str, required=True, help="IP address of this player"
    )
    parser.add_argument(
        "-o",
        "--next-player-ip",
        type=str,
        required=True,
        help="IP address of the next player in the game",
    )

    args = parser.parse_args()

    network = Network(args.player_id, args.player_ip, args.next_player_ip)
    game = Game(args.player_id, network)

    game.start()


if __name__ == "__main__":
    main()
