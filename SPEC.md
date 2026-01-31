We will build a clone of Whispr Flow called WhOSSpr flow where the OSS is for open source.

Namely this will be an application that allows users to convert speech to text in a convenient manner across their entire desktop experience.

The application should be configured and optimized to work in a mac primarily and it's not as important to get support in other operating systems or devices - we will prioritise functionality in the current setup primarily.

Initially we will build it such that the entire application is a terminal CLI for simplicity with a JSON based config that can be used for startup which can also be provided as command-line parameters. However it shoudl still be built modularly in case that this was to be extended such that a user interface is to interact with the backend and the CLI is another way of interacting (but for now it's the primary way)

The basic functionality will be to leverage a local Whispr model, which can be configured locally; you should be able to select the size of the whispr model to use for the inference, and these would run locally on the mac.

This means that in the mac it should request permissions like "Accessibility" in order to control the computer and inject keystrokes to applications, as well as "Access to the microphone".

You should also be able to configure the keyboard shortcut which would allow for enabling dictation when held, as well as keyboard shortcut to toggle dictation on and off.

In regards to access, it should be able to inject the text to most applications, including web browsers, terminal, and code editors, between others, it should all work.

By default the text to speech will read directly from the whispr model and inject it to the respective applications. However we should also be able to provide it access to a remote openAI compatible API with authentication token which should be able to run the text through to improve the text; for this we should also have a default System prompt that can be used, which should be also as a separate file in the repo but should also allow the user to modify the sysetm prompt; when running with this enabled then the dictation should work in batches - initially it should do it all at once, but then we can explore sliding windows or other approaches.

You can also review other codebases to identify approachse and best practices which have tackled similar problems, such as the following:

* https://github.com/prasanjit101/whishpy?tab=readme-ov-file
* And many other whispr clones

As well as the whisper resources:

* https://github.com/openai/whisper

Tech stack:

* Preferred mostly python
* There is a venv uv set up already in the folder
* Git is configured
* Pytest
* Typer
* Other relevant libraries

This is quite a comprehensive request, so please ensure that before starting you put together a comprehensive plan to move forward, and a design plan on how this will fit the existing codebase. Create a set of tasks from the TODOs outlined below by number, and make sure you carry them out one by one without skipping any, each of them should ensure the tests are validated and passing, and committed with using commits using "comprehensive commit" style with succint and functional descriptions each individual task is done. Ensure that all tests pass, you have docker running locally so you can run all the end-to-end tests as well as the unit tests across the repo. We are still in alpha so breaking changes can be done and migration does not need to be documented.
