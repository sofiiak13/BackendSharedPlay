from main import get_yt_data  
if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=WXS-o57VJ5w&list=RDWXS-o57VJ5w"
    # video_url = "https://music.youtube.com/watch?v=NQxS_nwPZzI&si=Nd9yOAZ30UH3UdtO"
    result = get_yt_data(video_url)
    print(result)