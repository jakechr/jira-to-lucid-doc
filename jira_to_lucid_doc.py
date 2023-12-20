from dotenv import load_dotenv
import lucid_client
import arg_utils
    
load_dotenv()

args = arg_utils.parse_args()
response_json = lucid_client.create_lucid_board(args)

print(f"Access the new document at: {response_json['editUrl']}")