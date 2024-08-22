import typer

from .commands import merge, config, impose

app = typer.Typer(no_args_is_help=True)

app.command(no_args_is_help=True)(merge.merge)
app.command(no_args_is_help=True)(impose.impose)
app.command()(config.config)

if __name__ == "__main__":
    app()
