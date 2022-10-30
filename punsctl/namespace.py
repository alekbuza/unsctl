# -*- coding: utf-8 -*-
# Copyright (c) 2022 Aleksandar Buza <me@aleksandarbuza.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import logging
from os import mkdir, readlink, rmdir
from pathlib import Path
from typing import List

from punsctl.rootspace import RootSpace
from punsctl.static import CURRENT_NS_SYMLINK_NAME
from punsctl.utils import func_rename_path, func_symlink_path, func_unlink_path

__all__ = ["Namespace", "NamespaceException"]


class NamespaceException(Exception):
    def __init__(self, message):
        self.message = message


class Namespace(object):
    def __init__(
        self,
        name: str,
        root_space: RootSpace,
    ):
        self.name = name
        self.root_space = root_space

        self.symlink_path = root_space.get_symlink_path()
        self.current_ns_path = root_space.get_current_ns_path()
        self.path = Path(f"{root_space.get_path()}/{name}")

        logging.debug(f"debug: namespace name: {self.name}")
        logging.debug(f"debug: namespace path: {self.path}")

    def create(self) -> None:
        try:
            mkdir(self.path, mode=0o744)

        except OSError as exc:
            raise NamespaceException(message=exc.strerror)

    def remove(self) -> None:
        try:
            if self.exists():
                logging.debug(f"debug: mkdir: {self.path}")
                rmdir(self.path)

        except OSError as exc:
            raise NamespaceException(message=exc.strerror)

    def exists(self) -> bool:
        if not self.path.exists():
            return False

        return True

    def get_path(self) -> Path:
        return self.path

    def active(self) -> bool:
        if (
            self.current_ns_path.exists()
            and Path(readlink(self.current_ns_path)) == self.path
        ):
            return True

        return False

    def get_name(self) -> str:
        return self.name

    def get_namespace_path(self) -> Path:
        return self.path

    def __get_sources(self) -> List[Path]:
        sources = []

        for source in self.path.iterdir():
            if source.name == self.current_ns_path.name:
                continue
            sources.append(source)

        return sources

    def activate(self) -> None:
        if not self.exists():
            raise NamespaceException(
                message=f"{self.name} ({self.path}) doesn't exists"
            )

        if self.current_ns_path.exists() and self.current_ns_path.is_symlink():
            if Path(readlink(self.current_ns_path)) == self.path:
                pass

            else:
                raise NamespaceException(
                    message=(
                        f"{self.root_space.get_current_ns_name()} "
                        f"namespace is already activated"
                    )
                )
        else:
            self.current_ns_path.symlink_to(self.path)

        for source in self.__get_sources():
            if source.name == CURRENT_NS_SYMLINK_NAME:
                continue

            with Path(f"{self.symlink_path}/{source.name}") as target:
                if target.exists():
                    if target.is_symlink() and Path(readlink(target)) == source:
                        continue

                    with target.with_name(f"{target.name}.{self.name}.bak") as backup:
                        if not backup.exists():
                            logging.debug(f"debug: rename {target} -> {backup}")
                            func_rename_path(path=target, target=backup)

                        else:
                            continue

                if not target.is_symlink():
                    logging.debug(f"debug: symlink {target} -> {source}")
                    func_symlink_path(target=target, source=source)

    def deactivate(self) -> None:
        for source in self.__get_sources():
            with Path(f"{self.symlink_path}/{source.name}") as target:
                if target.exists():
                    if target.is_symlink() and Path(readlink(target)) == source:
                        logging.debug(f"debug: unlink {target}")
                        func_unlink_path(symlink=target)

                    with target.with_name(f"{target.name}.{self.name}.bak") as backup:
                        if backup.exists() and not backup.is_symlink():
                            if target.exists():
                                continue

                            logging.debug(f"debug: rename {target} -> {backup}")
                            func_rename_path(path=backup, target=target)

        if self.current_ns_path.exists() and self.current_ns_path.is_symlink():
            if Path(readlink(self.current_ns_path)) == self.path:
                logging.debug(f"debug: unlink {self.current_ns_path}")
                func_unlink_path(symlink=self.current_ns_path)
