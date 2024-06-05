import typer

from .commands import merge, config

app = typer.Typer(no_args_is_help=True)

app.command(no_args_is_help=True)(merge.merge)
app.command()(config.config)

if __name__ == "__main__":
    app()
