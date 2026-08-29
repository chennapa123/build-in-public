from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from buildinpublic.generator import SocialMediaPosts
from buildinpublic.publishers.base import BasePublisher

console = Console()


class ConsolePublisher(BasePublisher):
    """Console / Dry-Run Publisher that renders formatted posts to terminal."""

    def name(self) -> str:
        return "Console / Terminal Output"

    def publish(self, posts: SocialMediaPosts, dry_run: bool = True) -> bool:
        mode_str = " (Dry-Run)" if dry_run else ""
        
        console.print("\n" + "=" * 60)
        console.print(Panel(posts.title, title="[bold magenta]Title / Hook[/bold magenta]"))
        console.print(Panel(posts.x_post, title=f"[bold cyan]X / Twitter Post{mode_str}[/bold cyan]"))
        console.print(Panel(Markdown(posts.linkedin_post), title=f"[bold blue]LinkedIn Post{mode_str}[/bold blue]"))
        console.print("=" * 60 + "\n")

        return True
