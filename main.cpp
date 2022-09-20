#include <iostream>
#include <filesystem>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <string>

#include <tgbot/tgbot.h>

using namespace std;
using namespace TgBot;

void spotdl(Bot& bot, Message::Ptr message){
    cout << "download started\n";
    std::filesystem::current_path("../music");
    system("rm *.mp3");
    string link = message->text;
    string command = "spotdl " + link;
    system(command.c_str());
    cout << "downloaded ended\n";
    system("ls -d \"$PWD\"/*.mp3 > list");
    cout << "new list made\n";
    ifstream in("list");
    if(in.fail()){
        cout << "error in opening list\n";
    }else{
        cout << "upload started\n";
        string item;
        while(getline(in, item)){
            cout << "sending \"" << item;
            bot.getApi().sendAudio(message->chat->id, InputFile::fromFile(item, "audio/mpeg"));
            cout << "\"done\n";
        }
        cout << "upload ended\n";
    }
}

int main() {
    cout << std::filesystem::current_path() << endl;
    string token(getenv("NM80_MUSIC_BOT_API"));
    printf("Token: %s\n", token.c_str());

    Bot bot(token);
    bot.getEvents().onCommand("start", [&bot](Message::Ptr message) {
        bot.getApi().sendMessage(message->chat->id, "Hi!");
    });
    bot.getEvents().onAnyMessage([&bot](Message::Ptr message) {
        printf("User wrote %s\n", message->text.c_str());
        if (StringTools::startsWith(message->text, "/start")) {
            return;
        }
        spotdl(bot, message);
    });

    signal(SIGINT, [](int s) {
        printf("SIGINT got\n");
        exit(0);
    });

    try {
        printf("Bot username: %s\n", bot.getApi().getMe()->username.c_str());
        bot.getApi().deleteWebhook();

        TgLongPoll longPoll(bot);
        while (true) {
            printf("Long poll started\n");
            longPoll.start();
        }
    } catch (exception& e) {
        printf("error: %s\n", e.what());
    }

    return 0;
}