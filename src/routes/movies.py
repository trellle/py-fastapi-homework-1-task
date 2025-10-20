from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence

from src.database import get_db
from src.database import MovieModel
from src.schemas import MovieDetailResponseSchema, MovieListResponseSchema


router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер сторінки"),
    per_page: int = Query(
        10, ge=1, le=20, description="Кількість фільмів на сторінку"
    )
) -> Sequence[MovieModel]:
    total_items = await db.scalar(select(func.count()).select_from(MovieModel))
    total_pages = (total_items + per_page - 1) // per_page
    if page < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=[{
            "loc": ["query", "page"],
            "msg": f"ensure that 1 <= page <= {total_pages}",
            "type": "value_error.number.not_ge"
        }])
    if per_page < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=[{
            "loc": ["query", "per_page"],
            "msg": "ensure per+_page is greater than or equal to 1",
            "type": "value_error.number.not_ge"
        }])
    offset = (page - 1) * per_page
    result = await db.execute(select(MovieModel).offset(offset).limit(per_page))
    movies = result.scalars().all()
    if not movies or page > total_pages and total_pages != 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No movies found.")
    base_url = str(request.url).split("?")[0]
    return MovieListResponseSchema(
        movies=movies,
        prev_page=f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"{base_url}?page={page + 1}&per_page={per_page}" if page <= total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get("/movies/{movie_id}/", response_model=MovieDetailResponseSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")
    return movie
