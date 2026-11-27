#pragma once
namespace NativeMenu {
inline const char* divaDescription() {
    const char* language="english";
    auto steam=GetModuleHandleW(L"steam_api64.dll");
    if(steam) {
        auto apps=reinterpret_cast<void*(*)()>(GetProcAddress(steam,"SteamAPI_SteamApps_v008"));
        auto getLanguage=reinterpret_cast<const char*(*)(void*)>(GetProcAddress(steam,"SteamAPI_ISteamApps_GetCurrentGameLanguage"));
        if(apps && getLanguage) if(auto instance=apps()) if(auto value=getLanguage(instance)) language=value;
    }
    struct Translation { const char* language; const char8_t* text; };
    static const Translation translations[]={
        {"spanish",u8"¡Entra en la DIVA ROOM e interactúa con tu VOCALOID favorita!"},
        {"latam",u8"¡Entra en la DIVA ROOM e interactúa con tu VOCALOID favorita!"},
        {"english",u8"Enter the DIVA ROOM and interact with your favorite VOCALOID!"},
        {"french",u8"Entre dans la DIVA ROOM et interagis avec ta VOCALOID préférée !"},
        {"german",u8"Betritt den DIVA ROOM und verbringe Zeit mit deiner Lieblings-VOCALOID!"},
        {"italian",u8"Entra nella DIVA ROOM e interagisci con la tua VOCALOID preferita!"},
        {"japanese",u8"DIVA ROOMに入って、お気に入りのVOCALOIDとふれあおう！"},
        {"koreana",u8"DIVA ROOM에 들어가 좋아하는 VOCALOID와 교감해 보세요!"},
        {"schinese",u8"进入DIVA ROOM，与你最喜欢的VOCALOID互动吧！"},
        {"tchinese",u8"進入DIVA ROOM，與你最喜歡的VOCALOID互動吧！"}
    };
    for(const auto& entry:translations) if(!strcmp(language,entry.language)) return reinterpret_cast<const char*>(entry.text);
    return reinterpret_cast<const char*>(translations[2].text);
}
}
