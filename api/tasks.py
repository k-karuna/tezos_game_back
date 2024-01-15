from celery import shared_task
from api.models import GameSession


@shared_task
def end_game_session(game_hash):
    game = GameSession.objects.get(hash=game_hash)
    if game.seconds_on_pause != 0:
        end_game_session.s(game.hash).apply_async(countdown=game.seconds_on_pause)
        game.seconds_on_pause = 0
        game.save()
        return f'Gaming session {game_hash} pause seconds setted to 0.'

    if game.status == GameSession.ENDED:
        return f'Gaming session {game_hash} already ended.'
    elif game.status in {GameSession.CREATED, GameSession.PAUSED}:
        game.status = GameSession.ABANDONED
        game.save()
        return f'Gaming session {game_hash} successfully abandoned.'
