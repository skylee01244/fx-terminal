from bot.core import SaxoTradingBot

def main():
    print("-" * 60)
    print("FX Trading Terminal")
    print("\nSelect Data Source:")
    print("1) Saxo API      - Live trading with real account")
    print("2) Yahoo Finance - Paper trading with $1M demo account")
    print("-" * 60)
    
    choice = input("\nEnter (1 or 2): ").strip()
    
    if choice == "1":
        token = input("Saxo API Token: ").strip()
        
        if not token:
            print("[NO INPUT]")
            return
        print()
        bot = SaxoTradingBot(token, data_source_type="saxo")
        bot.run()
        
    elif choice == "2":
        print("Starting balance: $1,000,000")
        print("Real-time data from Yahoo Finance")
        
        bot = SaxoTradingBot("", data_source_type="yahoo")
        bot.run()
        
    else:
        print("[INVALID]")

if __name__ == "__main__":
    main()
