package com.shabby.service;

import com.alibaba.fastjson.JSONObject;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public interface RecycleService {
    JSONObject selectAll(Integer userId);

    void recoverImage(Integer userId,List<Integer> imageIds );

    void deleteImage(Integer userId,List<Integer> imageIds );

}
