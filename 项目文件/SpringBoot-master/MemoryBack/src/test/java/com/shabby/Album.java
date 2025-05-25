package com.shabby;

import com.shabby.dao.AlbumMapper;
import com.shabby.service.AlbumService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import javax.annotation.Resource;
import java.util.List;

@SpringBootTest
public class Album {

    @Resource
    AlbumService albumService;
    @Resource
    AlbumMapper albumMapper;
    @Test
    void selectAlbumPart(){

//        List<AlbumImageVO> albumImageVOS = albumMapper.selectAlbumImage(1);
//        System.out.println(albumImageVOS);

    }
}
