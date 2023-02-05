import tarfile
from io import BytesIO


def get_dir_as_tar(path: str) -> BytesIO:
    x = BytesIO()
    with tarfile.open(fileobj=x, mode='w:gz') as file:
        file.add(path, arcname='')
    x.seek(0)
    return x


def extract_tar_from_bytesio(bytes_io: BytesIO, dst_path: str) -> None:
    bytes_io.seek(0)
    with tarfile.open(fileobj=bytes_io, mode='r:gz') as file:
        file.extractall(dst_path)
