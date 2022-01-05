# AutoXuexiPlaywright

## What is this?

A script to finish XuexiQiangguo's everyday task automatically.

## How to use?

Install requirements in `requirements.txt`, run `AutoXuexiPlaywrightHeadless.py` or `AutoXuexiPlaywrightGUI.pyw`, the first one doesn't have GUI while the second one has. If you don't have Desktop Environment in Linux, you have to use headless version. If you are using headless version, `PySide6` is not a requirement and you can remove it.

## About Proxy

``` text
proxy sample:
[
    {
        "server":"socks5://127.0.0.1:20808,
        "username":"user",
        "password:"pwd"
    },
    ......
]

OR

None
```

~~We will add a GUI config editor soon.~~  
We have added a GUI config editor and it should work as expected. If you are using headless version, please check config format before saving file.

## About async API

We use Playwright as backend, it provides an async API. We will try to use this instead sync API to improve IO performance. It is in early development phase and has many problems, if you are just a common user, we recommend you keep it disabled.

## Notes

1. This tool is under heavy development and may not as stable as other tools. Some fratures may also don't work as expected. Everyone's pull request to improve this tool is welcome.

2. This tool is designed only finishing tasks listed on [website](https://xuexi.cn), your max score in one day is 45 after using this tool correctly because some tasks are only available on mobile app.

3. This tool is just for researching purpose, we don't be responsible for any result by using this tool.

4. This tool is also available on [multiverse](https://github.com/multiverse-vcs/go-multiverse), a decentralized VCS which is also under heavy development, with address `12D3KooWSBwQcHfgKLVMWNc9wLdqpFQmfy7mjAcBznQpdjZNwC9M/AutoXuexiPlaywright`, you can setup a multiverse node and use it to provide mirror service. We don't guarantee the availablity on GitHub.
